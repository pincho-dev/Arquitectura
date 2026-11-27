from abc import ABC, abstractmethod


class EspecieLookup(ABC):
    @abstractmethod
    def obtener_rangos(self, nombre_especie):
        pass
class EspecieNoEncontrada(Exception):
    pass
class CatalogoEspecies(ABC):
    @abstractmethod
    def listar(self):
        pass

class RepositorioUsuarios(ABC):
    @abstractmethod
    def buscar_por_email(self, email):
        """Devuelve el Usuario o None si no existe."""
        pass

    @abstractmethod
    def crear(self, nombre, email, password_hash):
        """Devuelve el Usuario creado. Lanza EmailYaRegistrado si el email ya existe."""
        pass
class HasherContrasenas(ABC):
    @abstractmethod
    def hashear(self, password):
        pass

    @abstractmethod
    def verificar(self, password, password_hash):
        pass

class EmisorTokens(ABC):
    # El dominio solo sabe que se emite "un token" para un usuario:
    # no sabe que es JWT ni cómo se firma.
    @abstractmethod
    def emitir_para_usuario(self, usuario_id):
        pass


class RepositorioPlantas(ABC):
    @abstractmethod
    def crear(self, nombre, especie, usuario_id):
        """Crea la planta con usuario_id como dueño. Lanza EspecieNoEncontrada."""
        pass

    @abstractmethod
    def buscar(self, planta_id):
        """Devuelve la Planta (con sus dueños) o None."""
        pass

    @abstractmethod
    def listar_de_usuario(self, usuario_id):
        pass

    @abstractmethod
    def eliminar(self, planta_id):
        pass

    @abstractmethod
    def agregar_dueno(self, planta_id, usuario_id):
        """No hace nada si el usuario ya es dueño."""
        pass
    @abstractmethod
    def renombrar(self, planta_id, nombre):
        pass

class HistorialLecturas(ABC):
    @abstractmethod
    def guardar(self, lectura):
        """Lanza LecturaDuplicada si el dispositivo ya reportó esa misma marca de tiempo."""
        pass

    @abstractmethod
    def ultima(self, planta_id):
        """Devuelve la Lectura más reciente o None."""
        pass

    @abstractmethod
    def listar(self, planta_id, limite):
        """Lecturas más recientes primero."""
        pass

class RepositorioDispositivos(ABC):
    @abstractmethod
    def registrar(self, codigo, planta_id, token):
        """Guarda el dispositivo (y solo el hash del token). Lanza CodigoDispositivoEnUso."""
        pass

    @abstractmethod
    def listar_de_planta(self, planta_id):
        pass

    @abstractmethod
    def registrar_de_fabrica(self, codigo, especie, token, clave_reclamo, rfid_uid=None):
        """Matera sin dueño todavía, identificada por la tarjeta RFID rfid_uid.
        Lanza CodigoDispositivoEnUso, TarjetaRfidEnUso o EspecieNoEncontrada."""
        pass

    @abstractmethod
    def buscar_por_rfid(self, rfid_uid):
        """Devuelve el Dispositivo no revocado con esa tarjeta RFID, o None."""
        pass

    @abstractmethod
    def buscar_para_reclamo(self, codigo, clave_reclamo):
        """Devuelve el Dispositivo (con su especie de fábrica) si la clave
        corresponde al código, o None."""
        pass

    @abstractmethod
    def asignar_planta(self, dispositivo_id, planta_id):
        """Devuelve False si otro usuario la reclamó primero."""
        pass

    @abstractmethod
    def buscar_por_codigo(self, codigo):
        """Devuelve el Dispositivo no revocado con ese código, o None."""
        pass

    @abstractmethod
    def descartar_sin_reclamar(self, codigo):
        """Borra una matera de fábrica que nadie reclamó (ej. la estación no pudo
        generar su QR). Devuelve False si no existe o ya tiene dueño."""
        pass

class GeneradorTokensDispositivo(ABC):
    @abstractmethod
    def generar(self):
        pass

    @abstractmethod
    def generar_clave_reclamo(self):
        pass


class NotificadorUsuarios(ABC):
    """Avisos en vivo para un usuario (todas sus pestañas abiertas). El dominio
    no sabe que se entregan por WebSocket."""
    @abstractmethod
    def notificar(self, usuario_id, evento):
        pass


class CanalDispositivos(ABC):
    """Materas conectadas en este momento por un canal permanente (WebSocket)."""
    @abstractmethod
    def presencia(self, codigo):
        """Devuelve (en_linea, desconectada_en): si la matera tiene el canal
        abierto ahora y, si no, cuándo lo cerró por última vez (None si nunca
        se conectó por este canal desde que arrancó el servidor)."""
        pass

    @abstractmethod
    def enviar_orden(self, codigo, orden):
        """Devuelve el id de la orden. Lanza DispositivoDesconectado."""
        pass


class DatosLiga(ABC):
    """Lo que la liga necesita leer: quién participa y los estados de sus
    materas. El dominio no sabe que salen de la tabla de lecturas."""
    @abstractmethod
    def participantes(self, usuario_ids=None):
        """Lista de Participante. Con usuario_ids: esos usuarios activos, tengan
        o no plantas. Sin él: todos los usuarios activos con al menos una planta."""
        pass

    @abstractmethod
    def estados(self, planta_ids, desde, hasta):
        """{planta_id: [(medida_en, estado), ...]} en orden, solo lecturas de
        materas (no del formulario) con desde <= medida_en < hasta."""
        pass


class RepositorioAmistades(ABC):
    @abstractmethod
    def buscar(self, amistad_id):
        """Devuelve la Amistad o None."""
        pass

    @abstractmethod
    def buscar_entre(self, usuario_a, usuario_b):
        """La Amistad entre los dos (en cualquier sentido) o None."""
        pass

    @abstractmethod
    def crear(self, solicitante_id, destinatario_id):
        """Devuelve la Amistad pendiente. Lanza SolicitudYaExiste."""
        pass

    @abstractmethod
    def aceptar(self, amistad_id, cuando):
        pass

    @abstractmethod
    def eliminar(self, amistad_id):
        pass

    @abstractmethod
    def listar_de_usuario(self, usuario_id):
        """Todas las amistades donde participa, pendientes y aceptadas."""
        pass

    @abstractmethod
    def ids_amigos(self, usuario_id):
        """Conjunto de ids de sus amigos (solo amistades aceptadas)."""
        pass


class ProcesadorImagenes(ABC):
    @abstractmethod
    def normalizar(self, contenido):
        """bytes -> ImagenNormalizada: valida por el contenido que sea una foto
        de un formato permitido, la endereza, la reduce y la vuelve a codificar
        SIN metadatos (EXIF/GPS). Lanza ImagenInvalida."""
        pass


class AlmacenFotos(ABC):
    """Dónde viven los archivos de las fotos. El dominio no sabe si es el
    disco del servidor o un servicio en la nube."""
    @abstractmethod
    def guardar(self, clave, contenido):
        pass

    @abstractmethod
    def abrir(self, clave):
        """Devuelve los bytes o None si no existe."""
        pass

    @abstractmethod
    def eliminar(self, clave):
        """No falla si ya no existe."""
        pass


class RepositorioFotos(ABC):
    @abstractmethod
    def crear(self, planta_id, autor_id, clave_archivo, tipo, ancho, alto, descripcion, lectura):
        """Devuelve la Foto creada."""
        pass

    @abstractmethod
    def buscar(self, foto_id):
        """Devuelve la Foto (con los dueños de su planta) o None."""
        pass

    @abstractmethod
    def listar(self, limite, antes_de=None, planta_id=None):
        """Las más recientes primero. antes_de: id de la última foto ya vista
        (para "cargar más")."""
        pass

    @abstractmethod
    def eliminar(self, foto_id):
        pass
