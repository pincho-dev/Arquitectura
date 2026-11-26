"""Adaptador de entrada HTTP para la estación de fábrica (fabrica/estacion.py).

Hace lo mismo que `flask fabricar-matera`, pero para el programa que corre en
el PC con el lector NFC por USB: reservar una matera, grabar su sticker y,
si la grabación falla, descartarla. Las dos entradas usan el mismo caso de uso
FabricarMatera: es otro adaptador, no otra lógica.

Se protege con la cabecera X-Fabrica-Clave (FABRICA_CLAVE del .env). No usa
JWT de usuario: la fábrica no es un usuario de la app.
"""
import hmac

from flask import Blueprint, jsonify, request

from domain.plantas import CodigoDispositivoEnUso, DatosDePlantaInvalidos, MateraYaReclamada
from domain.puertos import EspecieNoEncontrada
from presentation.http import ErrorDeEntrada, error_json, leer_objeto, leer_texto
from presentation.sticker import url_sticker


def crear_api_fabrica(fabricar_matera, descartar_matera, clave_fabrica, url_front):
    api = Blueprint("fabrica", __name__, url_prefix="/api/fabrica")

    @api.before_request
    def _exigir_clave():
        if not clave_fabrica:
            return error_json("FABRICA_DESHABILITADA", "Falta FABRICA_CLAVE en el .env del backend.", 503)
        enviada = request.headers.get("X-Fabrica-Clave", "")
        if not hmac.compare_digest(enviada.encode(), clave_fabrica.encode()):
            return error_json("NO_AUTORIZADO", "Clave de fábrica inválida.", 401)

    @api.errorhandler(ErrorDeEntrada)
    def _entrada_invalida(e):
        return error_json("PARAMETRO_INVALIDO", str(e), 400, campo=e.campo)

    @api.errorhandler(DatosDePlantaInvalidos)
    def _datos_invalidos(e):
        return error_json("PARAMETRO_INVALIDO", str(e), 400, campo=e.campo)

    @api.errorhandler(EspecieNoEncontrada)
    def _especie(e):
        return error_json("ESPECIE_NO_SOPORTADA", str(e), 404, campo="especie")

    @api.errorhandler(CodigoDispositivoEnUso)
    def _codigo_en_uso(e):
        return error_json("DISPOSITIVO_YA_EXISTE", str(e), 409, campo="codigo")

    @api.errorhandler(MateraYaReclamada)
    def _no_descartable(e):
        return error_json("MATERA_NO_DESCARTABLE", str(e), 409, campo="codigo")

    @api.route("/materas", methods=["POST"])
    def fabricar():
        datos = leer_objeto(request.get_json(silent=True))
        codigo = datos.get("codigo")
        if codigo is not None and not isinstance(codigo, str):
            raise ErrorDeEntrada("El parámetro 'codigo' debe ser texto.", campo="codigo")
        codigo = codigo or _codigo_aleatorio()
        dispositivo, token, clave = fabricar_matera.ejecutar(codigo, leer_texto(datos, "especie"))
        return jsonify({
            "codigo": dispositivo.codigo,
            "especie": dispositivo.especie,
            # Se entrega una sola vez: en la BD solo quedan los hashes.
            "token_firmware": token,
            "url_sticker_nfc": url_sticker(url_front, dispositivo.codigo, clave),
        }), 201

    @api.route("/materas/<codigo>", methods=["DELETE"])
    def descartar(codigo):
        descartar_matera.ejecutar(codigo)
        return "", 204

    return api


def _codigo_aleatorio():
    import secrets
    return f"MAT-{secrets.token_hex(3).upper()}"
