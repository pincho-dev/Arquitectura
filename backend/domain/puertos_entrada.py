"""
Puertos de entrada: lo que la aplicación ofrece al mundo exterior.

Los adaptadores de entrada (API del front, API de dispositivos, pruebas)
dependen de estas interfaces, no de las clases concretas de application/.
Reciben identidades ya verificadas (usuario_id, Dispositivo), nunca tokens.
"""
from abc import ABC, abstractmethod


class RegistrarLecturaPort(ABC):
    @abstractmethod
    def desde_formulario(self, usuario_id, planta_id, humedad, luz, temperatura, medida_en):
        """Devuelve el Diagnostico. Lanza PlantaNoEncontrada, AccesoDenegado, ValorFueraDeRangoFisico."""
        pass

    @abstractmethod
    def desde_dispositivo(self, dispositivo, humedad, luz, temperatura, medida_en):
        """El dispositivo ya está autenticado y solo reporta para su propia planta."""
        pass

class ConsultarEstadoPlantaPort(ABC):
    @abstractmethod
    def ejecutar(self, usuario_id, planta_id):
        """Devuelve un ResumenPlanta con historial. Lanza PlantaNoEncontrada, AccesoDenegado."""
        pass

class ListarPlantasPort(ABC):
    @abstractmethod
    def ejecutar(self, usuario_id):
        """Devuelve un ResumenPlanta (sin historial) por cada planta del usuario."""
        pass

class CrearPlantaPort(ABC):
    @abstractmethod
    def ejecutar(self, usuario_id, nombre, especie):
        pass

class VincularDispositivoPort(ABC):
    @abstractmethod
    def ejecutar(self, usuario_id, planta_id, codigo):
        """Devuelve (Dispositivo, token). El token solo se entrega esta vez."""
        pass

class DiagnosticarPlantaPort(ABC):
    @abstractmethod
    def ejecutar(self, especie, humedad, luz, temperatura):
        """Validación de la fase 1 (R1): devuelve un Diagnostico sin guardar nada."""
        pass

class ListarEspeciesPort(ABC):
    @abstractmethod
    def ejecutar(self):
        pass

class RegistrarUsuarioPort(ABC):
    @abstractmethod
    def ejecutar(self, nombre, email, password):
        """Devuelve (Usuario, token)."""
        pass

class IniciarSesionPort(ABC):
    @abstractmethod
    def ejecutar(self, email, password):
        """Devuelve (Usuario, token). Lanza CredencialesInvalidas."""
        pass

class FabricarMateraPort(ABC):
    @abstractmethod
    def ejecutar(self, codigo, especie):
        """Devuelve (Dispositivo, token, clave_reclamo): el token va al firmware
        y la clave al sticker NFC. Ninguno se puede volver a consultar."""
        pass

class ReclamarMateraPort(ABC):
    @abstractmethod
    def ejecutar(self, usuario_id, codigo, clave_reclamo, nombre=None, especie=None):
        """El usuario se vuelve dueño de la matera: crea su planta y le asigna
        el dispositivo. Devuelve (Planta, Dispositivo)."""
        pass
