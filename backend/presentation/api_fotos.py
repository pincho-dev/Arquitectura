"""Adaptador de entrada REST de la galería de fotos. Todas las rutas exigen JWT
de usuario, incluida la imagen: el front la pide con fetch y la muestra como blob."""
from flask import Blueprint, Response, g, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

from domain.fotos import TAMANO_MAXIMO_BYTES, DatosDeFotoInvalidos, FotoNoEncontrada, ImagenInvalida
from domain.plantas import AccesoDenegado, PlantaNoEncontrada
from presentation.api_plantas import TEXTO_ESTADO
from presentation.http import ErrorDeEntrada, error_json

LIMITE_POR_DEFECTO = 24


def crear_api_fotos(subir_foto, listar_fotos, ver_foto, eliminar_foto, requiere_usuario):
    api = Blueprint("fotos", __name__, url_prefix="/api")

    @api.errorhandler(ErrorDeEntrada)
    def _entrada_invalida(e):
        return error_json("PARAMETRO_INVALIDO", str(e), 400, campo=e.campo)

    @api.errorhandler(DatosDeFotoInvalidos)
    def _datos_invalidos(e):
        return error_json("PARAMETRO_INVALIDO", str(e), 400, campo=e.campo)

    @api.errorhandler(ImagenInvalida)
    def _imagen_invalida(e):
        return error_json("IMAGEN_INVALIDA", str(e), 400, campo="foto")

    @api.errorhandler(RequestEntityTooLarge)
    def _muy_grande(e):
        return error_json("IMAGEN_INVALIDA",
                          f"La foto pesa más de {TAMANO_MAXIMO_BYTES // (1024 * 1024)} MB.", 413, campo="foto")

    @api.errorhandler(PlantaNoEncontrada)
    def _planta_no_encontrada(e):
        return error_json("PLANTA_NO_ENCONTRADA", str(e), 404)

    @api.errorhandler(FotoNoEncontrada)
    def _foto_no_encontrada(e):
        return error_json("FOTO_NO_ENCONTRADA", str(e), 404)

    @api.errorhandler(AccesoDenegado)
    def _acceso_denegado(e):
        return error_json("ACCESO_DENEGADO", str(e), 403)

    @api.route("/plantas/<int:planta_id>/fotos", methods=["POST"])
    @requiere_usuario
    def subir(planta_id):
        archivo = request.files.get("foto")
        if archivo is None:
            raise ErrorDeEntrada("Falta el archivo 'foto' (multipart/form-data).", campo="foto")
        foto = subir_foto.ejecutar(g.usuario_id, planta_id, archivo.read(), request.form.get("descripcion"))
        return jsonify(_foto_json(foto, g.usuario_id)), 201

    @api.route("/fotos", methods=["GET"])
    @requiere_usuario
    def listar():
        fotos = listar_fotos.ejecutar(
            _leer_entero("limite", LIMITE_POR_DEFECTO), _leer_entero("antes_de"), _leer_entero("planta"),
        )
        return jsonify([_foto_json(f, g.usuario_id) for f in fotos])

    @api.route("/fotos/<int:foto_id>/imagen", methods=["GET"])
    @requiere_usuario
    def imagen(foto_id):
        foto, contenido = ver_foto.ejecutar(foto_id)
        respuesta = Response(contenido, mimetype=foto.tipo)
        # La foto de un id nunca cambia: el navegador puede guardarla, pero solo para este usuario.
        respuesta.headers["Cache-Control"] = "private, max-age=86400, immutable"
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        respuesta.headers["Content-Security-Policy"] = "default-src 'none'"
        return respuesta

    @api.route("/fotos/<int:foto_id>", methods=["DELETE"])
    @requiere_usuario
    def eliminar(foto_id):
        eliminar_foto.ejecutar(g.usuario_id, foto_id)
        return "", 204

    return api


def _leer_entero(nombre, por_defecto=None):
    texto = request.args.get(nombre)
    if texto is None:
        return por_defecto
    if not texto.isdigit():
        raise ErrorDeEntrada(f"El parámetro '{nombre}' debe ser un entero positivo.", campo=nombre)
    return int(texto)


def _foto_json(foto, usuario_id):
    lectura = None
    if foto.lectura is not None:
        l = foto.lectura
        lectura = {
            "estado": l["estado"],
            "estado_texto": TEXTO_ESTADO.get(l["estado"], l["estado"]),
            "humedad": l["humedad"],
            "luz": l["luz"],
            "temperatura": l["temperatura"],
            "medida_en": l["medida_en"].isoformat() if l["medida_en"] else None,
        }
    return {
        "id": foto.id,
        "planta": {"id": foto.planta_id, "nombre": foto.planta_nombre, "especie": foto.especie},
        "autor": {"id": foto.autor_id, "nombre": foto.autor_nombre},
        "descripcion": foto.descripcion,
        "ancho": foto.ancho,
        "alto": foto.alto,
        "creada_en": foto.creada_en.isoformat() if foto.creada_en else None,
        "lectura": lectura,
        "puede_borrar": foto.puede_borrar(usuario_id),
        "imagen_url": f"/api/fotos/{foto.id}/imagen",
    }
