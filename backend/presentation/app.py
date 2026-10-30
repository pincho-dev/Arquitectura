from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
import os

from application.consultar_plantas import ConsultarEstadoPlanta, ListarPlantas
from application.crear_planta import CrearPlanta
from application.diagnosticar_planta import DiagnosticarPlanta
from application.registrar_lectura import RegistrarLectura
from application.vincular_dispositivo import VincularDispositivo
from application.iniciar_sesion import IniciarSesion
from application.registrar_usuario import RegistrarUsuario
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
from presentation.api_plantas import crear_api_plantas
from presentation.seguridad import crear_requiere_usuario

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = Flask(__name__)
CORS(app, origins=os.environ.get("CORS_ORIGIN", "*"))

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
registrar_lectura = RegistrarLectura(repositorio_plantas, historial_lecturas, caso_de_uso)

app.register_blueprint(crear_api_plantas(
    ListarPlantas(repositorio_plantas, historial_lecturas, repositorio_dispositivos, caso_de_uso),
    ConsultarEstadoPlanta(repositorio_plantas, historial_lecturas, repositorio_dispositivos, caso_de_uso),
    CrearPlanta(repositorio_plantas),
    registrar_lectura,
    VincularDispositivo(repositorio_plantas, repositorio_dispositivos, GeneradorTokensDispositivoAleatorio()),
    requiere_usuario,
))

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
