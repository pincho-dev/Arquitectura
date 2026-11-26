"""
Adaptador de salida WebSocket hacia el front:  ws://<servidor>:5000/ws/app

El navegador no puede poner la cabecera Authorization en un WebSocket, así
que el JWT va en el primer mensaje (y no en la URL, para que no quede en los
logs del servidor):

  app -> backend
    {"tipo": "auth", "token": "<JWT>"}       (primero, < 10 s)
    {"tipo": "ping"}                          (opcional: pide el estado completo otra vez)

  backend -> app
    {"tipo": "estado", "dispositivos": [{codigo, planta_id, conectado, ultima_conexion}]}
    {"tipo": "conexion", "planta_id": 3, "codigo": "MAT-1A2B", "conectado": false}
    {"tipo": "lectura",  "planta_id": 3, "codigo": "MAT-1A2B", "lectura": {medida_en, humedad, luz, temperatura, estado, origen}}
    {"tipo": "orden_ok", "planta_id": 3, "codigo": "MAT-1A2B", "id": "a1b2c3d4"}

Cada usuario recibe solo avisos de sus plantas (las propias y las compartidas
con él): AvisarDuenos busca los dueños de la planta en cada aviso.
"""
from infrastructure.tokens_jwt import ALCANCE_USUARIO, TokenInvalido
from presentation.http import ahora_utc
from presentation.ws_dispositivos import (
    CIERRE_NO_AUTORIZADO, CIERRE_PROTOCOLO, ESPERA_SALUDO_S, cerrar_con_error, parsear,
)


def registrar_websocket_app(sock, canal_app, tokens, listar_plantas, canal_dispositivos):

    def estado_inicial(usuario_id):
        ahora = ahora_utc()
        return {
            "tipo": "estado",
            "dispositivos": [
                {
                    "codigo": d.codigo,
                    "planta_id": resumen.planta.id,
                    "conectado": d.esta_conectado(ahora, canal_dispositivos.presencia(d.codigo)),
                    "ultima_conexion": d.ultima_conexion.isoformat() if d.ultima_conexion else None,
                }
                for resumen in listar_plantas.ejecutar(usuario_id)
                for d in resumen.dispositivos
            ],
        }

    @sock.route("/ws/app")
    def ws_app(ws):
        primero = parsear(ws.receive(timeout=ESPERA_SALUDO_S))
        if not primero or primero.get("tipo") != "auth":
            return cerrar_con_error(ws, CIERRE_PROTOCOLO, "AUTH_REQUERIDO",
                                    'El primer mensaje debe ser {"tipo": "auth", "token": "<JWT>"}.')
        token = primero.get("token")
        try:
            if not isinstance(token, str):
                raise TokenInvalido("Falta el token.")
            usuario_id = tokens.verificar(token, ALCANCE_USUARIO)
        except TokenInvalido as error:
            return cerrar_con_error(ws, CIERRE_NO_AUTORIZADO, "NO_AUTENTICADO", str(error))

        conexion = canal_app.registrar(usuario_id, ws)
        try:
            conexion.enviar(estado_inicial(usuario_id))
            while True:
                mensaje = parsear(ws.receive())
                if mensaje and mensaje.get("tipo") == "ping":
                    # El JWT se revisa de nuevo: una sesión vencida no sigue recibiendo avisos.
                    try:
                        tokens.verificar(token, ALCANCE_USUARIO)
                    except TokenInvalido as error:
                        return cerrar_con_error(ws, CIERRE_NO_AUTORIZADO, "NO_AUTENTICADO", str(error))
                    conexion.enviar(estado_inicial(usuario_id))
        finally:
            canal_app.retirar(usuario_id, conexion)

    return ws_app
