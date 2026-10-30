from domain.plantas import PlantaNoEncontrada, ResumenPlanta
from domain.puertos_entrada import ConsultarEstadoPlantaPort, ListarPlantasPort

LIMITE_HISTORIAL = 20


class _ArmadorDeResumen:
    def __init__(self, repositorio_plantas, historial, repositorio_dispositivos, diagnosticar):
        self.repositorio_plantas = repositorio_plantas
        self.historial = historial
        self.repositorio_dispositivos = repositorio_dispositivos
        self.diagnosticar = diagnosticar

    def _resumir(self, planta, con_historial):
        ultima = self.historial.ultima(planta.id)
        diagnostico = None
        if ultima is not None:
            # Se recalcula desde la lectura guardada para devolver también el
            # detalle por parámetro y las recomendaciones.
            diagnostico = self.diagnosticar.ejecutar(planta.especie, ultima.humedad, ultima.luz, ultima.temperatura)
        return ResumenPlanta(
            planta = planta,
            ultima_lectura = ultima,
            diagnostico = diagnostico,
            dispositivos = self.repositorio_dispositivos.listar_de_planta(planta.id),
            historial = self.historial.listar(planta.id, LIMITE_HISTORIAL) if con_historial else ()
        )


class ListarPlantas(_ArmadorDeResumen, ListarPlantasPort):

    def ejecutar(self, usuario_id):
        return [self._resumir(planta, con_historial=False)
                for planta in self.repositorio_plantas.listar_de_usuario(usuario_id)]


class ConsultarEstadoPlanta(_ArmadorDeResumen, ConsultarEstadoPlantaPort):

    def ejecutar(self, usuario_id, planta_id):
        planta = self.repositorio_plantas.buscar(planta_id)
        if planta is None:
            raise PlantaNoEncontrada(f"La planta {planta_id} no existe.")
        planta.verificar_acceso(usuario_id)
        return self._resumir(planta, con_historial=True)
