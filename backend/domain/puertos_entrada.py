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
    
class RenombrarPlantaPort(ABC):
    @abstractmethod
    def ejecutar(self, usuario_id, planta_id, nombre):
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
    def ejecutar(self, codigo, especie, rfid_uid=None):
        """Devuelve (Dispositivo, token, clave_reclamo): el token va al firmware
        y la clave al QR de la etiqueta. Ninguno se puede volver a consultar."""
        pass

class IdentificarMateraPort(ABC):
    @abstractmethod
    def ejecutar(self, rfid_uid):
        """Qué matera tiene pegada esta tarjeta RFID. Lanza TarjetaRfidDesconocida."""
        pass

class ReclamarMateraPort(ABC):
    @abstractmethod
    def ejecutar(self, usuario_id, codigo, clave_reclamo, nombre=None, especie=None):
        """El usuario se vuelve dueño de la matera: crea su planta y le asigna
        el dispositivo. Devuelve (Planta, Dispositivo)."""
        pass

class CompartirPlantaPort(ABC):
    @abstractmethod
    def ejecutar(self, usuario_id, planta_id, correo_invitado):
        """Un dueño agrega a otro usuario registrado como co-dueño.
        Devuelve la Planta actualizada. Lanza AccesoDenegado, InvitadoNoRegistrado."""
        pass


class EnviarOrdenPort(ABC):
    @abstractmethod
    def ejecutar(self, usuario_id, codigo, nombre_orden, parametros=None):
        """Devuelve el id de la orden enviada a la matera."""
        pass


class DescartarMateraPort(ABC):
    @abstractmethod
    def ejecutar(self, codigo):
        pass


class ConsultarMiLigaPort(ABC):
    @abstractmethod
    def ejecutar(self, usuario_id, ahora, anio=None, mes=None):
        """Devuelve MiLiga (puntos, división y detalle por planta). Sin mes: el actual.
        Lanza PeriodoInvalido."""
        pass


class ConsultarRankingPort(ABC):
    @abstractmethod
    def ejecutar(self, usuario_id, alcance, ahora, anio=None, mes=None):
        """Devuelve un Ranking "global" o entre "amigos" (que incluye al usuario).
        Lanza AlcanceInvalido, PeriodoInvalido."""
        pass


class ListarAmistadesPort(ABC):
    @abstractmethod
    def ejecutar(self, usuario_id):
        pass


class SolicitarAmistadPort(ABC):
    @abstractmethod
    def ejecutar(self, usuario_id, correo, ahora):
        """Devuelve la Amistad. Si la otra persona ya le había enviado una
        solicitud, la acepta. Lanza AmigoNoRegistrado, SolicitudInvalida,
        SolicitudYaExiste, YaSonAmigos."""
        pass


class AceptarAmistadPort(ABC):
    @abstractmethod
    def ejecutar(self, usuario_id, amistad_id, ahora):
        """Solo el destinatario acepta. Lanza AmistadNoEncontrada."""
        pass


class EliminarAmistadPort(ABC):
    @abstractmethod
    def ejecutar(self, usuario_id, amistad_id):
        """Rechazar, cancelar o dejar de ser amigos. Lanza AmistadNoEncontrada."""
        pass


class SubirFotoPort(ABC):
    @abstractmethod
    def ejecutar(self, usuario_id, planta_id, contenido, descripcion=None):
        """Devuelve la Foto. Lanza PlantaNoEncontrada, AccesoDenegado, ImagenInvalida,
        DatosDeFotoInvalidos."""
        pass


class ListarFotosPort(ABC):
    @abstractmethod
    def ejecutar(self, limite, antes_de=None, planta_id=None):
        pass


class VerFotoPort(ABC):
    @abstractmethod
    def ejecutar(self, foto_id):
        """Devuelve (Foto, bytes). Lanza FotoNoEncontrada."""
        pass


class EliminarFotoPort(ABC):
    @abstractmethod
    def ejecutar(self, usuario_id, foto_id):
        """Lanza FotoNoEncontrada, AccesoDenegado."""
        pass
