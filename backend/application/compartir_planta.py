from domain.plantas import InvitadoNoRegistrado, Planta, PlantaNoEncontrada
from domain.puertos_entrada import CompartirPlantaPort


class CompartirPlanta(CompartirPlantaPort):

    def __init__(self, repositorio_plantas, repositorio_usuarios):
        self.repositorio_plantas = repositorio_plantas
        self.repositorio_usuarios = repositorio_usuarios

    def ejecutar(self, usuario_id, planta_id, correo_invitado):
        planta = self.repositorio_plantas.buscar(planta_id)
        if planta is None:
            raise PlantaNoEncontrada(f"La planta {planta_id} no existe.")
        # Solo un dueño puede compartir: la misma regla de propiedad de siempre.
        planta.verificar_acceso(usuario_id)

        invitado = self.repositorio_usuarios.buscar_por_email(correo_invitado.strip().lower())
        if invitado is None or not invitado.activo:
            raise InvitadoNoRegistrado(f"No hay ninguna cuenta registrada con el correo '{correo_invitado.strip()}'.")

        self.repositorio_plantas.agregar_dueno(planta.id, invitado.id)
        return Planta(planta.id, planta.nombre, planta.especie, planta.duenos | {invitado.id})
