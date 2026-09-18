from collections import deque
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from flask_cors import CORS
import os

from application.diagnosticar_planta import DiagnosticarPlanta
from infrastructure.especie_lookup_csv import EspecieLookupCsv
from domain.modelos import ValorFueraDeRangoFisico
from domain.puertos import EspecieNoEncontrada
from application.listar_especies import ListarEspecies

app = Flask(__name__)
CORS(app, origins=os.environ.get("CORS_ORIGIN", "*"))

especie_lookup = EspecieLookupCsv()
caso_de_uso = DiagnosticarPlanta(especie_lookup)
caso_de_uso_especies = ListarEspecies(especie_lookup)

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
