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