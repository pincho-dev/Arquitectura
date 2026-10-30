"""
Verificación del JWT en el adaptador de entrada (R7).

El decorador lee la cabecera Authorization, valida el token y deja en
flask.g solo el id ya verificado. Los casos de uso reciben ese id, nunca el
token ni las cabeceras HTTP: el dominio no sabe que existe JWT.
"""
from functools import wraps

from flask import g, jsonify, request

from infrastructure.tokens_jwt import ALCANCE_USUARIO, TokenInvalido


def crear_requiere_usuario(tokens):

    def requiere_usuario(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            cabecera = request.headers.get("Authorization", "")
            esquema, _, token = cabecera.partition(" ")
            if esquema.lower() != "bearer" or not token:
                return _no_autorizado("Falta el token de acceso (Authorization: Bearer <token>).")
            try:
                g.usuario_id = tokens.verificar(token.strip(), ALCANCE_USUARIO)
            except TokenInvalido as error:
                return _no_autorizado(str(error))
            return vista(*args, **kwargs)
        return envoltura

    return requiere_usuario


def _no_autorizado(mensaje):
    respuesta = jsonify({"error": "NO_AUTORIZADO", "mensaje": mensaje, "detalle": {}})
    respuesta.headers["WWW-Authenticate"] = "Bearer"
    return respuesta, 401
