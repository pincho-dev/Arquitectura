from domain.ordenes import DispositivoDesconectado, Orden
from domain.plantas import PlantaNoEncontrada
from domain.puertos_entrada import EnviarOrdenPort


class EnviarOrden(EnviarOrdenPort):
    """El dueño de una planta le manda una orden (parpadear, reportar, regar)
    a una de sus materas mientras está conectada por WebSocket."""

    def __init__(self, repositorio_dispositivos, repositorio_plantas, canal):
        self.repositorio_dispositivos = repositorio_dispositivos
        self.repositorio_plantas = repositorio_plantas
        self.canal = canal

    def ejecutar(self, usuario_id, codigo, nombre_orden, parametros=None):
        codigo = codigo.strip().upper()
        dispositivo = self.repositorio_dispositivos.buscar_por_codigo(codigo)
        planta = self.repositorio_plantas.buscar(dispositivo.planta_id) if dispositivo and dispositivo.planta_id else None
        if planta is None:
            raise PlantaNoEncontrada(f"La matera {codigo} no existe o no tiene planta.")
        # Misma regla de propiedad que el resto (R7): solo un dueño de la planta.
        planta.verificar_acceso(usuario_id)

        orden = Orden(nombre_orden, parametros)
        en_linea, _ = self.canal.presencia(codigo)
        if not en_linea:
            raise DispositivoDesconectado(f"La matera {codigo} no está conectada en este momento.")
        return self.canal.enviar_orden(codigo, orden)
