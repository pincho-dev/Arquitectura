"""Avisos en vivo a los dueños de una planta (R6 en tiempo real).

Los casos de uso los disparan cuando algo cambia; el NotificadorUsuarios
(en producción, el WebSocket del front) los entrega a todas las pestañas
abiertas de cada dueño. Los dueños se buscan en cada aviso y no se guardan al
conectar el ESP32: la planta se puede compartir o la matera reclamar mientras
el ESP32 ya está conectado.
"""


def lectura_a_dict(lectura):
    return {
        "medida_en": lectura.medida_en.isoformat(),
        "humedad": lectura.humedad,
        "luz": lectura.luz,
        "temperatura": lectura.temperatura,
        "estado": lectura.estado,
        "origen": lectura.origen,
    }


class AvisarDuenos:
    def __init__(self, repositorio_plantas, notificador):
        self.repositorio_plantas = repositorio_plantas
        self.notificador = notificador

    def a_duenos_de(self, planta_id, evento):
        if planta_id is None:
            return  # matera sin reclamar: no hay a quién avisarle
        planta = self.repositorio_plantas.buscar(planta_id)
        if planta is None:
            return
        for usuario_id in planta.duenos:
            self.notificador.notificar(usuario_id, {"planta_id": planta_id, **evento})

    def conexion(self, dispositivo, conectado):
        self.a_duenos_de(dispositivo.planta_id, {
            "tipo": "conexion", "codigo": dispositivo.codigo, "conectado": conectado,
        })

    def lectura(self, lectura, codigo=None):
        self.a_duenos_de(lectura.planta_id, {
            "tipo": "lectura", "codigo": codigo, "lectura": lectura_a_dict(lectura),
        })

    def orden_cumplida(self, dispositivo, id_orden):
        self.a_duenos_de(dispositivo.planta_id, {
            "tipo": "orden_ok", "codigo": dispositivo.codigo, "id": id_orden,
        })


class AvisarDuenosNulo:
    """Para los tests y para correr sin tiempo real: no avisa a nadie."""

    def conexion(self, dispositivo, conectado):
        pass

    def lectura(self, lectura, codigo=None):
        pass

    def orden_cumplida(self, dispositivo, id_orden):
        pass
