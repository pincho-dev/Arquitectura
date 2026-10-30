import pytest

from application.iniciar_sesion import IniciarSesion
from application.registrar_usuario import RegistrarUsuario
from domain.puertos import EmisorTokens, HasherContrasenas, RepositorioUsuarios
from domain.usuarios import CredencialesInvalidas, DatosDeRegistroInvalidos, EmailYaRegistrado, Usuario


class _RepositorioUsuariosFalso(RepositorioUsuarios):
    def __init__(self):
        self.por_email = {}

    def buscar_por_email(self, email):
        return self.por_email.get(email)

    def crear(self, nombre, email, password_hash):
        if email in self.por_email:
            raise EmailYaRegistrado(email)
        usuario = Usuario(len(self.por_email) + 1, nombre, email, password_hash)
        self.por_email[email] = usuario
        return usuario


class _HasherFalso(HasherContrasenas):
    def hashear(self, password):
        return "hash:" + password

    def verificar(self, password, password_hash):
        return password_hash == "hash:" + password


class _EmisorTokensFalso(EmisorTokens):
    def emitir_para_usuario(self, usuario_id):
        return f"token-de-{usuario_id}"


@pytest.fixture
def repositorio():
    return _RepositorioUsuariosFalso()


@pytest.fixture
def registrar(repositorio):
    return RegistrarUsuario(repositorio, _HasherFalso(), _EmisorTokensFalso())


@pytest.fixture
def iniciar_sesion(repositorio):
    return IniciarSesion(repositorio, _HasherFalso(), _EmisorTokensFalso())


def test_registrar_guarda_hash_y_no_la_contrasena(registrar, repositorio):
    usuario, token = registrar.ejecutar("Ana", "ana@correo.com", "secreta123")

    assert token == f"token-de-{usuario.id}"
    assert repositorio.por_email["ana@correo.com"].password_hash == "hash:secreta123"


def test_registrar_normaliza_el_correo_a_minusculas(registrar, repositorio):
    registrar.ejecutar("Ana", "  Ana@Correo.COM ", "secreta123")

    assert "ana@correo.com" in repositorio.por_email


@pytest.mark.parametrize("nombre, correo, password, campo", [
    ("   ", "ana@correo.com", "secreta123", "nombre"),
    ("Ana", "sin-arroba", "secreta123", "correo"),
    ("Ana", "ana@correo.com", "corta", "password"),
    ("Ana", "ana@correo.com", "x" * 73, "password"),
])
def test_registrar_rechaza_datos_invalidos(registrar, nombre, correo, password, campo):
    with pytest.raises(DatosDeRegistroInvalidos) as error:
        registrar.ejecutar(nombre, correo, password)

    assert error.value.campo == campo


def test_registrar_dos_veces_el_mismo_correo_falla(registrar):
    registrar.ejecutar("Ana", "ana@correo.com", "secreta123")

    with pytest.raises(EmailYaRegistrado):
        registrar.ejecutar("Otra Ana", "ANA@correo.com", "secreta456")


def test_login_con_credenciales_correctas_devuelve_token(registrar, iniciar_sesion):
    registrado, _ = registrar.ejecutar("Ana", "ana@correo.com", "secreta123")

    usuario, token = iniciar_sesion.ejecutar("Ana@Correo.com", "secreta123")

    assert usuario.id == registrado.id
    assert token == f"token-de-{registrado.id}"


def test_login_con_contrasena_incorrecta_falla(registrar, iniciar_sesion):
    registrar.ejecutar("Ana", "ana@correo.com", "secreta123")

    with pytest.raises(CredencialesInvalidas):
        iniciar_sesion.ejecutar("ana@correo.com", "otra-clave")


def test_login_con_correo_inexistente_da_el_mismo_error(iniciar_sesion):
    with pytest.raises(CredencialesInvalidas) as error:
        iniciar_sesion.ejecutar("nadie@correo.com", "secreta123")

    assert str(error.value) == "Correo o contraseña incorrectos."


def test_login_de_usuario_inactivo_falla(registrar, iniciar_sesion, repositorio):
    registrar.ejecutar("Ana", "ana@correo.com", "secreta123")
    repositorio.por_email["ana@correo.com"].activo = False

    with pytest.raises(CredencialesInvalidas):
        iniciar_sesion.ejecutar("ana@correo.com", "secreta123")
