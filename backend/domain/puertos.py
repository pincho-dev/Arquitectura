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
