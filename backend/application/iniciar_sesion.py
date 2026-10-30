from domain.usuarios import CredencialesInvalidas


class IniciarSesion:

    def __init__(self, repositorio_usuarios, hasher, emisor_tokens):
        self.repositorio_usuarios = repositorio_usuarios
        self.hasher = hasher
        self.emisor_tokens = emisor_tokens

    def ejecutar(self, email, password):
        usuario = self.repositorio_usuarios.buscar_por_email(email.strip().lower())

        # Mismo error si el correo no existe o la contraseña falla: no se
        # revela qué correos están registrados.
        if usuario is None or not usuario.activo:
            raise CredencialesInvalidas("Correo o contraseña incorrectos.")
        if not self.hasher.verificar(password, usuario.password_hash):
            raise CredencialesInvalidas("Correo o contraseña incorrectos.")

        return usuario, self.emisor_tokens.emitir_para_usuario(usuario.id)
