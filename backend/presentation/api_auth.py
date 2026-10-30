"""Adaptador de entrada REST para registro e inicio de sesión (R7)."""
from flask import Blueprint, g, jsonify, request

from domain.usuarios import CredencialesInvalidas, DatosDeRegistroInvalidos, EmailYaRegistrado
from presentation.http import error_json as _error


def crear_api_auth(registrar_usuario, iniciar_sesion, requiere_usuario):
    api = Blueprint("auth", __name__, url_prefix="/api/auth")

    @api.route("/registro", methods=["POST"])
    def registro():
        datos, error = _leer_campos(("nombre", "correo", "password"))
        if error:
            return error
        try:
            usuario, token = registrar_usuario.ejecutar(datos["nombre"], datos["correo"], datos["password"])
        except DatosDeRegistroInvalidos as e:
            return _error("PARAMETRO_INVALIDO", str(e), 400, campo=e.campo)
        except EmailYaRegistrado as e:
            return _error("CORREO_YA_REGISTRADO", str(e), 409, campo="correo")
        return jsonify(_sesion(usuario, token)), 201

    @api.route("/login", methods=["POST"])
    def login():
        datos, error = _leer_campos(("correo", "password"))
        if error:
            return error
        try:
            usuario, token = iniciar_sesion.ejecutar(datos["correo"], datos["password"])
        except CredencialesInvalidas as e:
            return _error("CREDENCIALES_INVALIDAS", str(e), 401)
        return jsonify(_sesion(usuario, token))

    @api.route("/yo", methods=["GET"])
    @requiere_usuario
    def yo():
        return jsonify({"usuario_id": g.usuario_id})

    return api


def _leer_campos(campos):
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return None, _error("PARAMETRO_INVALIDO", "El cuerpo de la petición debe ser un JSON.", 400)
    for campo in campos:
        if not isinstance(datos.get(campo), str) or not datos[campo]:
            return None, _error("PARAMETRO_INVALIDO", f"Falta el parámetro '{campo}' o no es texto.", 400, campo=campo)
    return datos, None


def _sesion(usuario, token):
    # Nunca se devuelve el password_hash.
    return {
        "token": token,
        "tipo": "Bearer",
        "usuario": {"id": usuario.id, "nombre": usuario.nombre, "correo": usuario.email},
    }
