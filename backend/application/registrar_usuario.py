from domain.usuarios import DatosDeRegistroInvalidos
from domain.puertos_entrada import RegistrarUsuarioPort

LONGITUD_MINIMA_PASSWORD = 8
# bcrypt solo usa los primeros 72 bytes; más largo se rechaza en vez de truncarse en silencio.
BYTES_MAXIMOS_PASSWORD = 72


class RegistrarUsuario(RegistrarUsuarioPort):

    def __init__(self, repositorio_usuarios, hasher, emisor_tokens):
        self.repositorio_usuarios = repositorio_usuarios
        self.hasher = hasher
        self.emisor_tokens = emisor_tokens

    def ejecutar(self, nombre, email, password):
        nombre = nombre.strip()
        email = email.strip().lower()

        if not nombre:
            raise DatosDeRegistroInvalidos("El nombre no puede estar vacío.", campo="nombre")
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise DatosDeRegistroInvalidos("El correo no es válido.", campo="correo")
        if len(password) < LONGITUD_MINIMA_PASSWORD:
            raise DatosDeRegistroInvalidos(
                f"La contraseña debe tener al menos {LONGITUD_MINIMA_PASSWORD} caracteres.", campo="password"
            )
        if len(password.encode("utf-8")) > BYTES_MAXIMOS_PASSWORD:
            raise DatosDeRegistroInvalidos("La contraseña es demasiado larga.", campo="password")

        usuario = self.repositorio_usuarios.crear(nombre, email, self.hasher.hashear(password))
        return usuario, self.emisor_tokens.emitir_para_usuario(usuario.id)
