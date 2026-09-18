from flask import Flask, request, jsonify
from flask_cors import CORS
import os

from application.diagnosticar_planta import DiagnosticarPlanta
from infrastructure.especie_lookup_json import EspecieLookupJson
from domain.modelos import ValorFueraDeRangoFisico
from domain.puertos import EspecieNoEncontrada

app = Flask(__name__)
CORS(app, origins=os.environ.get("CORS_ORIGIN", "*"))

especie_lookup = EspecieLookupJson()
caso_de_uso = DiagnosticarPlanta(especie_lookup)

@app.route("/diagnostico", methods=["POST"])
def diagnostico():
    datos = request.get_json()
    try:
        resultado = caso_de_uso.ejecutar(
            especie=datos["especie"],
            humedad=datos["humedad"],
            luz=datos["luz"],
            temperatura=datos["temperatura"],
        )
    except EspecieNoEncontrada as error:
        return jsonify({"error": str(error)}), 404
    except ValorFueraDeRangoFisico as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({
        "especie": resultado.especie,
        "estado": resultado.estado,
        "recomendaciones": resultado.recomendaciones,
        "parametros": [
            {"nombre": p.nombre, "valor": p.valor, "unidad": p.unidad, "estado": p.estado}
            for p in resultado.parametros
        ],
    })