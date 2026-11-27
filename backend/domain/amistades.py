"""Amistades entre usuarios, para el ranking entre amigos.

Una amistad empieza como solicitud (aceptada_en = None) y queda aceptada
cuando el destinatario la acepta. Cualquiera de los dos puede borrarla:
así se rechaza, se cancela o se deja de ser amigos."""


class AmigoNoRegistrado(Exception):
    pass


class SolicitudInvalida(Exception):
    pass


class SolicitudYaExiste(Exception):
    pass


class YaSonAmigos(Exception):
    pass


class AmistadNoEncontrada(Exception):
    pass


class Amistad:
    def __init__(self, id, solicitante_id, solicitante_nombre, destinatario_id, destinatario_nombre,
                 aceptada_en=None, creada_en=None):
        self.id = id
        self.solicitante_id = solicitante_id
        self.solicitante_nombre = solicitante_nombre
        self.destinatario_id = destinatario_id
        self.destinatario_nombre = destinatario_nombre
        self.aceptada_en = aceptada_en
        self.creada_en = creada_en

    @property
    def aceptada(self):
        return self.aceptada_en is not None

    def participa(self, usuario_id):
        return usuario_id in (self.solicitante_id, self.destinatario_id)

    def otro(self, usuario_id):
        """(id, nombre) de la otra persona."""
        if usuario_id == self.solicitante_id:
            return self.destinatario_id, self.destinatario_nombre
        return self.solicitante_id, self.solicitante_nombre

    def estado_para(self, usuario_id):
        if self.aceptada:
            return "amigos"
        return "enviada" if usuario_id == self.solicitante_id else "recibida"
