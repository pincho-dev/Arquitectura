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
    def registrar_de_fabrica(self, codigo, especie, token, clave_reclamo):
        """Matera sin dueño todavía. Lanza CodigoDispositivoEnUso o EspecieNoEncontrada."""
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

class GeneradorTokensDispositivo(ABC):
    @abstractmethod
    def generar(self):
        pass

    @abstractmethod
    def generar_clave_reclamo(self):
        pass
