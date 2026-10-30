

class Usuario:
    def __init__(self, id, nombre, email, password_hash, activo=True):
        self.id = id
        self.nombre = nombre
        self.email = email
        self.password_hash = password_hash
        self.activo = activo

class DatosDeRegistroInvalidos(Exception):
    def __init__(self, mensaje, campo=None):
        super().__init__(mensaje)
        self.campo = campo

class EmailYaRegistrado(Exception):
    pass

class CredencialesInvalidas(Exception):
    pass
