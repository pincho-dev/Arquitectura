"""
Adaptador de entrada WebSocket de los ESP32:  ws://<servidor>:5000/ws/dispositivos

El ESP32 abre la conexión (el backend no puede llegar a él: está detrás del
router de la casa) y la deja abierta. Por ella viaja todo, en JSON:

  ESP32 -> backend
    {"tipo": "hola", "codigo": "MAT-1A2B", "token": "dev_...", "firmware": "2.0.0"}   (primero, < 10 s)
    {"tipo": "lectura", "humedad": 41.5, "luz": 380, "temperatura": 22.1}          (medida_en es opcional)
    {"tipo": "orden_ok", "id": "a1b2c3d4"}

  backend -> ESP32
    {"tipo": "bienvenida", "codigo": "MAT-1A2B", "reclamada": true, "intervalo_s": 10}
    {"tipo": "lectura_ok", "estado": "SALUDABLE"}
    {"tipo": "orden", "id": "a1b2c3d4", "orden": "parpadear", "parametros": {}}
    {"tipo": "error", "error": "MATERA_SIN_DUENO", "mensaje": "..."}

Saber si la matera está conectada deja de ser una suposición: mientras el
socket esté abierto, lo está. Si se apaga de golpe, el ping del servidor
(WS_PING_S) no recibe respuesta y la conexión se cierra.

Igual que el POST /api/dispositivos/<codigo>/lecturas, aquí solo se traduce
el protocolo: la lectura entra al mismo caso de uso RegistrarLectura.
"""
import json
import logging

from domain.modelos import ValorFueraDeRangoFisico
from domain.plantas import LecturaDuplicada, MateraSinDueno, PlantaNoEncontrada
from presentation.http import ErrorDeEntrada, ahora_utc, leer_fecha, leer_medicion

log = logging.getLogger("matera.ws")

ESPERA_SALUDO_S = 10
# Códigos de cierre 4000-4999: propios de la aplicación.
CIERRE_PROTOCOLO = 4400
CIERRE_NO_AUTORIZADO = 4401
CIERRE_ACCESO_DENEGADO = 4403


def parsear(texto):
    try:
        mensaje = json.loads(texto)
    except (TypeError, ValueError):
        return None
    return mensaje if isinstance(mensaje, dict) else None


def cerrar_con_error(ws, codigo_cierre, error, mensaje):
    try:
        ws.send(json.dumps({"tipo": "error", "error": error, "mensaje": mensaje}))
        ws.close(reason=codigo_cierre, message=mensaje[:100])
    except Exception:
        pass


def registrar_websocket_dispositivos(sock, autenticador, registrar_lectura, canal, avisos, intervalo_s):

    @sock.route("/ws/dispositivos")
    def ws_dispositivo(ws):
        # 1. Saludo: el ESP32 se identifica con su código y su token de fábrica.
        saludo = parsear(ws.receive(timeout=ESPERA_SALUDO_S))
        if not saludo or saludo.get("tipo") != "hola":
            return cerrar_con_error(ws, CIERRE_PROTOCOLO, "SALUDO_REQUERIDO",
                                    'El primer mensaje debe ser {"tipo": "hola", "codigo": ..., "token": ...}.')
        token, codigo = saludo.get("token"), saludo.get("codigo")
        dispositivo = autenticador.autenticar(token) if isinstance(token, str) and token else None
        if dispositivo is None:
            return cerrar_con_error(ws, CIERRE_NO_AUTORIZADO, "NO_AUTORIZADO", "Token de dispositivo inválido o revocado.")
        if not isinstance(codigo, str) or codigo.strip().upper() != dispositivo.codigo:
            return cerrar_con_error(ws, CIERRE_ACCESO_DENEGADO, "ACCESO_DENEGADO", "El token no corresponde a este dispositivo.")

        conexion = canal.registrar(dispositivo.codigo, ws)
        log.info("Matera %s conectada (firmware %s)", dispositivo.codigo, saludo.get("firmware", "?"))
        avisos.conexion(dispositivo, True)
        try:
            conexion.enviar({"tipo": "bienvenida", "codigo": dispositivo.codigo,
                             "reclamada": dispositivo.tiene_dueno(), "intervalo_s": intervalo_s})

            # 2. Mensajes mientras la conexión siga abierta.
            while True:
                mensaje = parsear(ws.receive())
                if mensaje is None:
                    conexion.enviar({"tipo": "error", "error": "MENSAJE_INVALIDO", "mensaje": "Se esperaba un objeto JSON."})
                    continue

                tipo = mensaje.get("tipo")
                if tipo == "lectura":
                    # Se vuelve a verificar el token en cada lectura: así una matera
                    # revocada se corta al instante, una reclamada mientras estaba
                    # conectada empieza a reportar sin reconectarse, y queda al día
                    # su ultima_conexion.
                    actual = autenticador.autenticar(token)
                    if actual is None:
                        return cerrar_con_error(ws, CIERRE_NO_AUTORIZADO, "NO_AUTORIZADO", "El token de la matera fue revocado.")
                    if actual.planta_id != dispositivo.planta_id:
                        avisos.conexion(actual, True)   # los dueños nuevos ven que ya está conectada
                    dispositivo = actual
                    conexion.enviar(_registrar(registrar_lectura, dispositivo, mensaje))
                elif tipo == "orden_ok":
                    log.info("Matera %s cumplió la orden %s", dispositivo.codigo, mensaje.get("id"))
                    avisos.orden_cumplida(dispositivo, mensaje.get("id"))
                else:
                    conexion.enviar({"tipo": "error", "error": "TIPO_DESCONOCIDO", "mensaje": f"Tipo '{tipo}' no soportado."})
        finally:
            if canal.retirar(dispositivo.codigo, conexion):
                log.info("Matera %s desconectada", dispositivo.codigo)
                avisos.conexion(dispositivo, False)

    return ws_dispositivo


def _registrar(registrar_lectura, dispositivo, mensaje):
    """Traduce el mensaje a la llamada del caso de uso y su resultado (o error) a la respuesta."""
    def error(codigo, texto):
        return {"tipo": "error", "error": codigo, "mensaje": texto}

    try:
        ahora = ahora_utc()
        medida_en = leer_fecha(mensaje, "medida_en", ahora) if "medida_en" in mensaje else ahora
        diagnostico = registrar_lectura.desde_dispositivo(dispositivo, medida_en=medida_en, **leer_medicion(mensaje))
    except (ErrorDeEntrada, ValorFueraDeRangoFisico) as e:
        return error("PARAMETRO_INVALIDO", str(e))
    except MateraSinDueno as e:
        return error("MATERA_SIN_DUENO", str(e))
    except LecturaDuplicada:
        return error("LECTURA_DUPLICADA", "Esa lectura ya se había recibido.")
    except PlantaNoEncontrada as e:
        return error("PLANTA_NO_ENCONTRADA", str(e))
    return {"tipo": "lectura_ok", "estado": diagnostico.estado, "recomendaciones": diagnostico.recomendaciones}
