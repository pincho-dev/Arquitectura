from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sock import Sock
import os

from application.avisos import AvisarDuenos
from application.compartir_planta import CompartirPlanta
from application.enviar_orden import EnviarOrden
from application.consultar_plantas import ConsultarEstadoPlanta, ListarPlantas
from application.crear_planta import CrearPlanta
from application.diagnosticar_planta import DiagnosticarPlanta
from application.registrar_lectura import RegistrarLectura
from application.vincular_dispositivo import VincularDispositivo
from application.iniciar_sesion import IniciarSesion
from application.materas import DescartarMatera, FabricarMatera, ReclamarMatera
from application.registrar_usuario import RegistrarUsuario
from infrastructure.autenticador_dispositivos_bd import AutenticadorDispositivosBd
from infrastructure.canal_websocket import CanalAppWebSocket, CanalDispositivosWebSocket
from infrastructure.db.conexion import crear_engine
from infrastructure.especie_lookup_bd import EspecieLookupBd
from infrastructure.especie_lookup_csv import EspecieLookupCsv
from infrastructure.hasher_bcrypt import HasherBcrypt
from infrastructure.historial_lecturas_bd import HistorialLecturasBd
from infrastructure.repositorio_dispositivos_bd import RepositorioDispositivosBd
from infrastructure.repositorio_plantas_bd import RepositorioPlantasBd
from infrastructure.tokens_dispositivo import GeneradorTokensDispositivoAleatorio
from infrastructure.repositorio_usuarios_bd import RepositorioUsuariosBd
from infrastructure.tokens_jwt import TokensJwt
from domain.modelos import ValorFueraDeRangoFisico
from domain.puertos import EspecieNoEncontrada
from application.listar_especies import ListarEspecies
from presentation.api_auth import crear_api_auth
from presentation.api_dispositivos import crear_api_dispositivos
from presentation.api_fabrica import crear_api_fabrica
from presentation.api_plantas import crear_api_mis_dispositivos, crear_api_plantas
from presentation.cli_fabrica import registrar_cli_fabrica
from presentation.seguridad import crear_requiere_usuario
from presentation.ws_app import registrar_websocket_app
from presentation.ws_dispositivos import registrar_websocket_dispositivos

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = Flask(__name__)
# Varios orígenes separados por coma: el front en el PC y en el teléfono (red local).
CORS(app, origins=[o.strip() for o in os.environ.get("CORS_ORIGIN", "*").split(",")])

# WebSockets (flask-sock). El servidor manda un ping cada WS_PING_S segundos:
# si el ESP32 (o la pestaña) no responde antes del siguiente, se cierra la
# conexión. Así se detecta una matera desenchufada de golpe.
app.config["SOCK_SERVER_OPTIONS"] = {"ping_interval": int(os.environ.get("WS_PING_S", "20"))}
sock = Sock(app)

# ---- Punto de composición: único lugar donde se decide qué adaptador
# ---- implementa cada puerto. El engine no abre conexión hasta usarse.
engine = crear_engine()


def _crear_tabla_referencia():
    # R4: el adaptador se elige por configuración, el dominio y los casos de uso no cambian.
    if os.environ.get("TABLA_REFERENCIA", "csv").lower() == "bd":
        return EspecieLookupBd(engine)
    return EspecieLookupCsv()


tokens = TokensJwt(os.environ.get("JWT_SECRET"), int(os.environ.get("JWT_MINUTOS_VALIDEZ", "60")))
repositorio_usuarios = RepositorioUsuariosBd(engine)
hasher = HasherBcrypt()
requiere_usuario = crear_requiere_usuario(tokens)

app.register_blueprint(crear_api_auth(
    RegistrarUsuario(repositorio_usuarios, hasher, tokens),
    IniciarSesion(repositorio_usuarios, hasher, tokens),
    requiere_usuario,
))

especie_lookup = _crear_tabla_referencia()
caso_de_uso = DiagnosticarPlanta(especie_lookup)
caso_de_uso_especies = ListarEspecies(especie_lookup)

repositorio_plantas = RepositorioPlantasBd(engine)
historial_lecturas = HistorialLecturasBd(engine)
repositorio_dispositivos = RepositorioDispositivosBd(engine)
generador_tokens_dispositivo = GeneradorTokensDispositivoAleatorio()

# Tiempo real: qué materas y qué pestañas tienen un WebSocket abierto.
canal_dispositivos = CanalDispositivosWebSocket()
canal_app = CanalAppWebSocket()
avisos = AvisarDuenos(repositorio_plantas, canal_app)

registrar_lectura = RegistrarLectura(repositorio_plantas, historial_lecturas, caso_de_uso, avisos)

listar_plantas = ListarPlantas(repositorio_plantas, historial_lecturas, repositorio_dispositivos, caso_de_uso)

app.register_blueprint(crear_api_plantas(
    listar_plantas,
    ConsultarEstadoPlanta(repositorio_plantas, historial_lecturas, repositorio_dispositivos, caso_de_uso),
    CrearPlanta(repositorio_plantas),
    registrar_lectura,
    VincularDispositivo(repositorio_plantas, repositorio_dispositivos, generador_tokens_dispositivo),
    ReclamarMatera(repositorio_dispositivos, repositorio_plantas),
    CompartirPlanta(repositorio_plantas, repositorio_usuarios),
    requiere_usuario,
    canal_dispositivos,
))
app.register_blueprint(crear_api_mis_dispositivos(
    listar_plantas, requiere_usuario,
    EnviarOrden(repositorio_dispositivos, repositorio_plantas, canal_dispositivos),
    canal_dispositivos,
))

# Fábrica: el mismo caso de uso por dos adaptadores de entrada, la consola
# (flask fabricar-matera) y la API de la estación con lector NFC (fabrica/).
url_front = os.environ.get("FRONT_URL", "http://localhost:5500")
fabricar_matera = FabricarMatera(repositorio_dispositivos, generador_tokens_dispositivo)
registrar_cli_fabrica(app, fabricar_matera, url_front)
app.register_blueprint(crear_api_fabrica(
    fabricar_matera, DescartarMatera(repositorio_dispositivos),
    os.environ.get("FABRICA_CLAVE", ""), url_front,
))

# Adaptadores de entrada de dispositivos (R2): HTTP y WebSocket reutilizan el
# mismo puerto RegistrarLecturaPort que el formulario del front.
autenticador_dispositivos = AutenticadorDispositivosBd(engine)
app.register_blueprint(crear_api_dispositivos(registrar_lectura, autenticador_dispositivos))
registrar_websocket_dispositivos(
    sock, autenticador_dispositivos, registrar_lectura, canal_dispositivos, avisos,
    intervalo_s=int(os.environ.get("ESP_INTERVALO_S", "10")),
)

# Adaptador de salida hacia el front: avisos en vivo por WebSocket.
registrar_websocket_app(sock, canal_app, tokens, listar_plantas, canal_dispositivos)

# Bitácora en memoria de las últimas solicitudes, solo para el panel de
# estado (GET /estado). No es persistencia de mediciones (fuera de
# alcance de este corte): se pierde al reiniciar el servidor.
SOLICITUDES_RECIENTES = deque(maxlen=20)


@app.after_request
def _registrar_solicitud(respuesta):
    if request.path != "/estado":
        SOLICITUDES_RECIENTES.appendleft({
            "metodo": request.method,
            "ruta": request.path,
            "estado": respuesta.status_code,
            "hora": datetime.now(timezone.utc).isoformat(),
        })
    return respuesta

CAMPOS_REQUERIDOS = ("especie", "humedad", "luz", "temperatura")
CAMPOS_NUMERICOS = ("humedad", "luz", "temperatura")


class ErrorDeValidacion(Exception):
    def __init__(self, mensaje, campo=None):
        super().__init__(mensaje)
        self.campo = campo


def _extraer_medicion(datos):
    if not isinstance(datos, dict):
        raise ErrorDeValidacion(
            "El cuerpo de la petición debe ser un JSON con especie, humedad, luz y temperatura."
        )

    for campo in CAMPOS_REQUERIDOS:
        if campo not in datos:
            raise ErrorDeValidacion(f"Falta el parámetro '{campo}'.", campo=campo)

    if not isinstance(datos["especie"], str) or not datos["especie"].strip():
        raise ErrorDeValidacion("El parámetro 'especie' debe ser un texto no vacío.", campo="especie")

    valores = {"especie": datos["especie"]}
    for campo in CAMPOS_NUMERICOS:
        try:
            valores[campo] = float(datos[campo])
        except (TypeError, ValueError):
            raise ErrorDeValidacion(f"El parámetro '{campo}' debe ser numérico.", campo=campo)

    return valores


def _error(codigo, mensaje, status, campo=None):
    return jsonify({"error": codigo, "mensaje": mensaje, "detalle": {"campo": campo}}), status


@app.route("/diagnostico", methods=["POST"])
def diagnostico():
    try:
        valores = _extraer_medicion(request.get_json(silent=True))
        resultado = caso_de_uso.ejecutar(**valores)
    except ErrorDeValidacion as error:
        return _error("PARAMETRO_INVALIDO", str(error), 400, campo=error.campo)
    except EspecieNoEncontrada as error:
        return _error("ESPECIE_NO_SOPORTADA", str(error), 404, campo="especie")
    except ValorFueraDeRangoFisico as error:
        return _error("PARAMETRO_INVALIDO", str(error), 400)

    return jsonify({
        "especie": resultado.especie,
        "estado": resultado.estado,
        "recomendaciones": resultado.recomendaciones,
        "parametros": [
            {"nombre": p.nombre, "valor": p.valor, "unidad": p.unidad, "estado": p.estado}
            for p in resultado.parametros
        ],
    })

@app.route("/especies", methods=["GET"])
def especies():
    return jsonify([
        {
            "nombre": r.nombre,
            "rangos": {
                "humedad": {"minimo": r.rango_humedad.minimo, "maximo": r.rango_humedad.maximo},
                "luz": {"minimo": r.rango_luz.minimo, "maximo": r.rango_luz.maximo},
                "temperatura": {"minimo": r.rango_temperatura.minimo, "maximo": r.rango_temperatura.maximo}
            }
        }
        for r in caso_de_uso_especies.ejecutar()
    ])


@app.route("/estado", methods=["GET"])
def estado():
    return jsonify({
        "servicio": "diagnostico-plantas",
        "activo": True,
        "especies_cargadas": len(caso_de_uso_especies.ejecutar()),
        "hora_servidor": datetime.now(timezone.utc).isoformat(),
        "solicitudes_recientes": list(SOLICITUDES_RECIENTES),
    })
