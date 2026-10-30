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

class DatosDePlantaInvalidos(Exception):
    def __init__(self, mensaje, campo=None):
        super().__init__(mensaje)
        self.campo = campo


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
    def __init__(self, id, codigo, planta_id, ultima_conexion=None, especie=None):
        self.id = id
        self.codigo = codigo
        self.planta_id = planta_id
        self.ultima_conexion = ultima_conexion
        # Especie del kit de fábrica; solo se usa al reclamar la matera.
        self.especie = especie

    def tiene_dueno(self):
        # Una matera sin planta todavía no pertenece a ningún usuario.
        return self.planta_id is not None

    def esta_conectado(self, ahora):
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
