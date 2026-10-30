import bcrypt

from domain.puertos import HasherContrasenas


class HasherBcrypt(HasherContrasenas):
    """Hash lento y con sal propia por contraseña (la sal queda dentro del hash)."""

    def hashear(self, password):
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verificar(self, password, password_hash):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except ValueError:
            return False
