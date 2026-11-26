from datetime import timedelta

ORIGEN_FORMULARIO = "formulario"
ORIGEN_DISPOSITIVO = "dispositivo"

# Un dispositivo cuenta como "conectado" si reportó dentro de esta ventana.
VENTANA_CONEXION = timedelta(minutes=2)


class PlantaNoEncontrada(Exception):
    pass

class AccesoDenegado(Exception):
    pass

class LecturaDuplicada(Exception):
    pass

class CodigoDispositivoEnUso(Exception):
    pass

class ClaveDeReclamoInvalida(Exception):
    pass

class MateraYaReclamada(Exception):
    pass

class MateraSinDueno(Exception):
    pass

class InvitadoNoRegistrado(Exception):
    pass

class TarjetaRfidEnUso(Exception):
    pass

class TarjetaRfidDesconocida(Exception):
    pass

class DatosDePlantaInvalidos(Exception):
    def __init__(self, mensaje, campo=None):
        super().__init__(mensaje)
        self.campo = campo


# Los UID de MIFARE miden 4, 7 o 10 bytes (8, 14 o 20 dígitos hexadecimales).
LARGOS_UID_RFID = (8, 14, 20)


def normalizar_uid_rfid(uid):
    """'04:a1 b2-c3' -> '04A1B2C3'. El lector puede mandarlo con separadores o
    en minúscula; en la BD queda siempre igual para que el UNIQUE funcione."""
    limpio = "".join(c for c in uid if c not in ": -").upper()
    if len(limpio) not in LARGOS_UID_RFID or any(c not in "0123456789ABCDEF" for c in limpio):
        raise DatosDePlantaInvalidos(
            "El UID de la tarjeta RFID debe ser hexadecimal de 4, 7 o 10 bytes (ej. 04A1B2C3).", campo="rfid_uid")
    return limpio


class Planta:
    def __init__(self, id, nombre, especie, duenos):
        self.id = id
        self.nombre = nombre
        self.especie = especie
        self.duenos = frozenset(duenos)

    def verificar_acceso(self, usuario_id):
        # Regla de negocio de R7: un usuario solo ve y modifica sus plantas.
        if usuario_id not in self.duenos:
            raise AccesoDenegado("No tienes acceso a esta planta.")


class Dispositivo:
    def __init__(self, id, codigo, planta_id, ultima_conexion=None, especie=None, rfid_uid=None):
        self.id = id
        self.codigo = codigo
        self.planta_id = planta_id
        self.ultima_conexion = ultima_conexion
        # Especie del kit de fábrica; solo se usa al reclamar la matera.
        self.especie = especie
        # UID de la tarjeta RFID que la fábrica le pegó a la matera (su "placa").
        self.rfid_uid = rfid_uid

    def tiene_dueno(self):
        # Una matera sin planta todavía no pertenece a ningún usuario.
        return self.planta_id is not None

    def esta_conectado(self, ahora, presencia=None):
        """presencia = (en_linea, desconectada_en) del canal WebSocket, si se
        conoce. Con WebSocket se sabe al instante; por HTTP solo se puede
        suponer que sigue conectado si reportó dentro de VENTANA_CONEXION."""
        if presencia is not None:
            en_linea, desconectada_en = presencia
            if en_linea:
                return True
            if desconectada_en is not None and (
                    self.ultima_conexion is None or self.ultima_conexion <= desconectada_en):
                # Cerró el WebSocket y no ha vuelto a reportar por ningún lado.
                return False
        return self.ultima_conexion is not None and ahora - self.ultima_conexion <= VENTANA_CONEXION


class Lectura:
    def __init__(self, planta_id, humedad, luz, temperatura, estado, medida_en,
                 origen, dispositivo_id=None, dispositivo_codigo=None):
        self.planta_id = planta_id
        self.humedad = humedad
        self.luz = luz
        self.temperatura = temperatura
        self.estado = estado
        self.medida_en = medida_en
        self.origen = origen
        self.dispositivo_id = dispositivo_id
        self.dispositivo_codigo = dispositivo_codigo


class ResumenPlanta:
    """Lo que se sabe de una planta en este momento: su última lectura y el
    diagnóstico de esa lectura (None si todavía no hay datos)."""

    def __init__(self, planta, ultima_lectura, diagnostico, dispositivos, historial=()):
        self.planta = planta
        self.ultima_lectura = ultima_lectura
        self.diagnostico = diagnostico
        self.dispositivos = list(dispositivos)
        self.historial = list(historial)
