"""
Conexiones WebSocket abiertas, en memoria.

  CanalDispositivosWebSocket   qué socket es de qué matera (para mandarle órdenes
                               y saber al instante si está conectada)
  CanalAppWebSocket            pestañas/celulares abiertos de cada usuario
                               (para empujarle avisos)

Limitación conocida (para el análisis de evolución): todo vive en el proceso
del servidor. Con varios procesos o servidores haría falta un broker
(Redis pub/sub o MQTT) entre ellos.
"""
import json
import threading
import uuid
from datetime import datetime, timezone

from domain.ordenes import DispositivoDesconectado
from domain.puertos import CanalDispositivos, NotificadorUsuarios


class Conexion:
    def __init__(self, ws):
        self.ws = ws
        self._lock = threading.Lock()   # un solo hilo escribe a la vez en el socket

    def enviar(self, mensaje):
        with self._lock:
            self.ws.send(json.dumps(mensaje))


class CanalDispositivosWebSocket(CanalDispositivos):

    def __init__(self):
        self._conexiones = {}
        self._desconectadas_en = {}
        self._lock = threading.Lock()

    def registrar(self, codigo, ws):
        """Asocia el socket a la matera. Si ya tenía otro (se reconectó antes de
        que el servidor notara la caída), cierra el viejo."""
        nueva = Conexion(ws)
        with self._lock:
            anterior = self._conexiones.get(codigo)
            self._conexiones[codigo] = nueva
        if anterior is not None:
            try:
                anterior.ws.close(reason=4000, message="Reemplazada por una conexión nueva")
            except Exception:
                pass
        return nueva

    def retirar(self, codigo, conexion):
        """True si era la conexión vigente, o sea, si la matera quedó desconectada
        (el socket viejo de una reconexión no cuenta como desconexión)."""
        with self._lock:
            if self._conexiones.get(codigo) is not conexion:
                return False
            del self._conexiones[codigo]
            self._desconectadas_en[codigo] = datetime.now(timezone.utc)
            return True

    def presencia(self, codigo):
        with self._lock:
            return codigo in self._conexiones, self._desconectadas_en.get(codigo)

    def enviar_orden(self, codigo, orden):
        with self._lock:
            conexion = self._conexiones.get(codigo)
        if conexion is None:
            raise DispositivoDesconectado(f"La matera {codigo} no está conectada en este momento.")
        id_orden = uuid.uuid4().hex[:8]
        try:
            conexion.enviar({"tipo": "orden", "id": id_orden, "orden": orden.nombre,
                             "parametros": orden.parametros})
        except Exception as error:
            raise DispositivoDesconectado(f"Se perdió la conexión con la matera {codigo}.") from error
        return id_orden


class CanalAppWebSocket(NotificadorUsuarios):

    def __init__(self):
        self._por_usuario = {}
        self._lock = threading.Lock()

    def registrar(self, usuario_id, ws):
        conexion = Conexion(ws)
        with self._lock:
            self._por_usuario.setdefault(usuario_id, set()).add(conexion)
        return conexion

    def retirar(self, usuario_id, conexion):
        with self._lock:
            conexiones = self._por_usuario.get(usuario_id)
            if conexiones is not None:
                conexiones.discard(conexion)
                if not conexiones:
                    del self._por_usuario[usuario_id]

    def notificar(self, usuario_id, evento):
        with self._lock:
            destinos = list(self._por_usuario.get(usuario_id, ()))
        for conexion in destinos:
            try:
                conexion.enviar(evento)
            except Exception:
                self.retirar(usuario_id, conexion)   # pestaña cerrada sin avisar
