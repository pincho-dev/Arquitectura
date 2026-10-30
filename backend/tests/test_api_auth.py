"""Endpoints de autenticación con dobles de prueba: no necesitan base de datos."""
import pytest
from flask import Flask

from application.iniciar_sesion import IniciarSesion
from application.registrar_usuario import RegistrarUsuario
from infrastructure.tokens_jwt import TokensJwt
from presentation.api_auth import crear_api_auth
from presentation.seguridad import crear_requiere_usuario
from tests.test_autenticacion import _HasherFalso, _RepositorioUsuariosFalso


@pytest.fixture
def client():
    repositorio, hasher, tokens = _RepositorioUsuariosFalso(), _HasherFalso(), TokensJwt("s" * 40)
    app = Flask(__name__)
    app.register_blueprint(crear_api_auth(
        RegistrarUsuario(repositorio, hasher, tokens),
        IniciarSesion(repositorio, hasher, tokens),
        crear_requiere_usuario(tokens),
    ))
    return app.test_client()


def _registrar(client, correo="ana@correo.com"):
    return client.post("/api/auth/registro", json={"nombre": "Ana", "correo": correo, "password": "secreta123"})


def test_registro_devuelve_201_con_token_y_sin_hash(client):
    respuesta = _registrar(client)

    assert respuesta.status_code == 201
    cuerpo = respuesta.get_json()
    assert cuerpo["token"]
    assert cuerpo["usuario"] == {"id": 1, "nombre": "Ana", "correo": "ana@correo.com"}
    assert "password" not in str(cuerpo)


def test_registro_con_correo_repetido_devuelve_409(client):
    _registrar(client)

    respuesta = _registrar(client)

    assert respuesta.status_code == 409
    assert respuesta.get_json()["error"] == "CORREO_YA_REGISTRADO"


def test_registro_sin_nombre_devuelve_400(client):
    respuesta = client.post("/api/auth/registro", json={"correo": "ana@correo.com", "password": "secreta123"})

    assert respuesta.status_code == 400
    assert respuesta.get_json()["detalle"]["campo"] == "nombre"


def test_login_correcto_y_token_abre_endpoint_protegido(client):
    _registrar(client)

    login = client.post("/api/auth/login", json={"correo": "ana@correo.com", "password": "secreta123"})
    token = login.get_json()["token"]
    yo = client.get("/api/auth/yo", headers={"Authorization": f"Bearer {token}"})

    assert login.status_code == 200
    assert yo.status_code == 200
    assert yo.get_json() == {"usuario_id": 1}


def test_login_incorrecto_devuelve_401(client):
    _registrar(client)

    respuesta = client.post("/api/auth/login", json={"correo": "ana@correo.com", "password": "mala-clave"})

    assert respuesta.status_code == 401
    assert respuesta.get_json()["error"] == "CREDENCIALES_INVALIDAS"


@pytest.mark.parametrize("cabecera", [None, "Bearer", "Basic abc", "Bearer token.falso.xyz"])
def test_endpoint_protegido_sin_token_valido_devuelve_401(client, cabecera):
    headers = {"Authorization": cabecera} if cabecera else {}

    respuesta = client.get("/api/auth/yo", headers=headers)

    assert respuesta.status_code == 401
    assert respuesta.get_json()["error"] == "NO_AUTORIZADO"
