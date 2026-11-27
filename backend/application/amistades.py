from domain.amistades import AmigoNoRegistrado, AmistadNoEncontrada, SolicitudInvalida, SolicitudYaExiste, YaSonAmigos
from domain.puertos_entrada import (
    AceptarAmistadPort, EliminarAmistadPort, ListarAmistadesPort, SolicitarAmistadPort,
)


class ListarAmistades(ListarAmistadesPort):

    def __init__(self, repositorio_amistades):
        self.repositorio_amistades = repositorio_amistades

    def ejecutar(self, usuario_id):
        return self.repositorio_amistades.listar_de_usuario(usuario_id)


class SolicitarAmistad(SolicitarAmistadPort):

    def __init__(self, repositorio_amistades, repositorio_usuarios):
        self.repositorio_amistades = repositorio_amistades
        self.repositorio_usuarios = repositorio_usuarios

    def ejecutar(self, usuario_id, correo, ahora):
        otro = self.repositorio_usuarios.buscar_por_email(correo.strip().lower())
        if otro is None or not otro.activo:
            raise AmigoNoRegistrado(f"No hay ninguna cuenta registrada con el correo '{correo.strip()}'.")
        if otro.id == usuario_id:
            raise SolicitudInvalida("No puedes enviarte una solicitud de amistad a ti mismo.")

        existente = self.repositorio_amistades.buscar_entre(usuario_id, otro.id)
        if existente is not None:
            if existente.aceptada:
                raise YaSonAmigos(f"Ya eres amigo de {otro.nombre}.")
            if existente.solicitante_id == usuario_id:
                raise SolicitudYaExiste(f"Ya le enviaste una solicitud a {otro.nombre}.")
            # La otra persona ya te la había enviado: enviarla de vuelta es aceptarla.
            self.repositorio_amistades.aceptar(existente.id, ahora)
            existente.aceptada_en = ahora
            return existente

        return self.repositorio_amistades.crear(usuario_id, otro.id)


class AceptarAmistad(AceptarAmistadPort):

    def __init__(self, repositorio_amistades):
        self.repositorio_amistades = repositorio_amistades

    def ejecutar(self, usuario_id, amistad_id, ahora):
        amistad = self.repositorio_amistades.buscar(amistad_id)
        # Al que no es el destinatario se le responde igual que si no existiera:
        # no tiene por qué saber qué solicitudes tienen los demás.
        if amistad is None or amistad.destinatario_id != usuario_id:
            raise AmistadNoEncontrada("No tienes esa solicitud de amistad.")
        if not amistad.aceptada:
            self.repositorio_amistades.aceptar(amistad.id, ahora)
            amistad.aceptada_en = ahora
        return amistad


class EliminarAmistad(EliminarAmistadPort):

    def __init__(self, repositorio_amistades):
        self.repositorio_amistades = repositorio_amistades

    def ejecutar(self, usuario_id, amistad_id):
        amistad = self.repositorio_amistades.buscar(amistad_id)
        if amistad is None or not amistad.participa(usuario_id):
            raise AmistadNoEncontrada("No tienes esa amistad ni esa solicitud.")
        self.repositorio_amistades.eliminar(amistad.id)
