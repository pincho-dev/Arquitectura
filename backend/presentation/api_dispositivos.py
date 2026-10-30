"""Adaptador de entrada para dispositivos (R2).

Traduce POST /api/dispositivos/<codigo>/lecturas a una llamada al puerto
RegistrarLecturaPort. No contiene reglas de negocio: autentica, traduce el
JSON y mapea errores a códigos HTTP. Agregarlo no modificó el dominio.
"""
from flask import Blueprint, jsonify, request

from domain.modelos import ValorFueraDeRangoFisico
from domain.plantas import LecturaDuplicada, PlantaNoEncontrada
from presentation.http import ErrorDeEntrada, ahora_utc, error_json, leer_fecha, leer_medicion, leer_objeto, leer_texto
from presentation.seguridad import extraer_bearer, no_autorizado


def crear_api_dispositivos(registrar_lectura, autenticador):
    api = Blueprint("dispositivos", __name__, url_prefix="/api/dispositivos")

    @api.errorhandler(ErrorDeEntrada)
    def _entrada_invalida(e):
        return error_json("PARAMETRO_INVALIDO", str(e), 400, campo=e.campo)

    @api.errorhandler(ValorFueraDeRangoFisico)
    def _fuera_de_rango_fisico(e):
        return error_json("PARAMETRO_INVALIDO", str(e), 400)

    @api.errorhandler(LecturaDuplicada)
    def _duplicada(e):
        return error_json("LECTURA_DUPLICADA", str(e), 409, campo="medida_en")

    @api.errorhandler(PlantaNoEncontrada)
    def _sin_planta(e):
        return error_json("PLANTA_NO_ENCONTRADA", str(e), 404)

    @api.route("/<codigo>/lecturas", methods=["POST"])
    def reportar_lectura(codigo):
        token = extraer_bearer()
        dispositivo = autenticador.autenticar(token) if token else None
        if dispositivo is None:
            return no_autorizado("Token de dispositivo inválido o revocado.")
        # El token define quién es el dispositivo; la URL no puede suplantarlo.
        if codigo.strip().upper() != dispositivo.codigo:
            return error_json("ACCESO_DENEGADO", "El token no corresponde a este dispositivo.", 403)

        datos = leer_objeto(request.get_json(silent=True))
        if leer_texto(datos, "dispositivo").strip().upper() != dispositivo.codigo:
            raise ErrorDeEntrada("El campo 'dispositivo' no coincide con el dispositivo autenticado.", campo="dispositivo")
        medida_en = leer_fecha(datos, "medida_en", ahora_utc())
        valores = leer_medicion(datos)

        diagnostico = registrar_lectura.desde_dispositivo(dispositivo, medida_en=medida_en, **valores)
        return jsonify({
            "dispositivo": dispositivo.codigo,
            "planta_id": dispositivo.planta_id,
            "estado": diagnostico.estado,
            "recomendaciones": diagnostico.recomendaciones,
        }), 201

    return api
