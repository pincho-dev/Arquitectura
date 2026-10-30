"""Adaptador de entrada REST del front para plantas, lecturas manuales y
vinculación de dispositivos. Todas las rutas exigen JWT de usuario."""
from flask import Blueprint, g, jsonify, request

from domain.modelos import ValorFueraDeRangoFisico
from domain.plantas import (
    AccesoDenegado, ClaveDeReclamoInvalida, CodigoDispositivoEnUso, DatosDePlantaInvalidos,
    MateraYaReclamada, PlantaNoEncontrada,
)
from domain.puertos import EspecieNoEncontrada
from presentation.http import ErrorDeEntrada, ahora_utc, error_json, leer_medicion, leer_objeto, leer_texto

ESTADO_SIN_DATOS = "SIN_DATOS"
TEXTO_ESTADO = {
    "SALUDABLE": "Saludable",
    "EN_RIESGO": "En riesgo",
    "CRITICO": "Crítico",
    ESTADO_SIN_DATOS: "Sin datos",
}


def crear_api_plantas(listar_plantas, consultar_estado, crear_planta, registrar_lectura,
                      vincular_dispositivo, reclamar_matera, requiere_usuario):
    api = Blueprint("plantas", __name__, url_prefix="/api/plantas")

    @api.errorhandler(ErrorDeEntrada)
    def _entrada_invalida(e):
        return error_json("PARAMETRO_INVALIDO", str(e), 400, campo=e.campo)

    @api.errorhandler(DatosDePlantaInvalidos)
    def _datos_invalidos(e):
        return error_json("PARAMETRO_INVALIDO", str(e), 400, campo=e.campo)

    @api.errorhandler(ValorFueraDeRangoFisico)
    def _fuera_de_rango_fisico(e):
        return error_json("PARAMETRO_INVALIDO", str(e), 400)

    @api.errorhandler(EspecieNoEncontrada)
    def _especie(e):
        return error_json("ESPECIE_NO_SOPORTADA", str(e), 404, campo="especie")

    @api.errorhandler(PlantaNoEncontrada)
    def _no_encontrada(e):
        return error_json("PLANTA_NO_ENCONTRADA", str(e), 404)

    @api.errorhandler(AccesoDenegado)
    def _acceso_denegado(e):
        return error_json("ACCESO_DENEGADO", str(e), 403)

    @api.errorhandler(CodigoDispositivoEnUso)
    def _codigo_en_uso(e):
        return error_json("DISPOSITIVO_YA_EXISTE", str(e), 409, campo="codigo")

    @api.errorhandler(ClaveDeReclamoInvalida)
    def _sticker_invalido(e):
        return error_json("STICKER_INVALIDO", str(e), 404, campo="clave")

    @api.errorhandler(MateraYaReclamada)
    def _ya_reclamada(e):
        return error_json("MATERA_YA_RECLAMADA", str(e), 409, campo="codigo")

    @api.route("", methods=["GET"])
    @requiere_usuario
    def listar():
        ahora = ahora_utc()
        return jsonify([_resumen_json(r, ahora) for r in listar_plantas.ejecutar(g.usuario_id)])

    @api.route("", methods=["POST"])
    @requiere_usuario
    def crear():
        datos = leer_objeto(request.get_json(silent=True))
        planta = crear_planta.ejecutar(g.usuario_id, leer_texto(datos, "nombre"), leer_texto(datos, "especie"))
        return jsonify(_planta_json(planta)), 201

    @api.route("/reclamar", methods=["POST"])
    @requiere_usuario
    def reclamar():
        # Lo que hace el front cuando el teléfono lee el sticker NFC de la matera.
        datos = leer_objeto(request.get_json(silent=True))
        planta, dispositivo = reclamar_matera.ejecutar(
            g.usuario_id, leer_texto(datos, "codigo"), leer_texto(datos, "clave"),
            nombre=datos.get("nombre") if isinstance(datos.get("nombre"), str) else None,
            especie=datos.get("especie") if isinstance(datos.get("especie"), str) else None,
        )
        return jsonify({**_planta_json(planta), "dispositivo": dispositivo.codigo}), 201

    @api.route("/<int:planta_id>/estado", methods=["GET"])
    @requiere_usuario
    def estado(planta_id):
        resumen = consultar_estado.ejecutar(g.usuario_id, planta_id)
        cuerpo = _resumen_json(resumen, ahora_utc())
        cuerpo["parametros"] = _parametros_json(resumen.diagnostico)
        cuerpo["historial"] = [_lectura_json(l) for l in resumen.historial]
        return jsonify(cuerpo)

    @api.route("/<int:planta_id>/lecturas", methods=["POST"])
    @requiere_usuario
    def registrar_desde_formulario(planta_id):
        valores = leer_medicion(leer_objeto(request.get_json(silent=True)))
        diagnostico = registrar_lectura.desde_formulario(g.usuario_id, planta_id, medida_en=ahora_utc(), **valores)
        return jsonify(_diagnostico_json(diagnostico)), 201

    @api.route("/<int:planta_id>/dispositivos", methods=["POST"])
    @requiere_usuario
    def vincular(planta_id):
        datos = leer_objeto(request.get_json(silent=True))
        dispositivo, token = vincular_dispositivo.ejecutar(g.usuario_id, planta_id, leer_texto(datos, "codigo"))
        return jsonify({
            "id": dispositivo.id,
            "codigo": dispositivo.codigo,
            "planta_id": dispositivo.planta_id,
            # Se muestra una única vez: en la BD solo queda su hash.
            "token": token,
        }), 201

    return api


def _planta_json(planta):
    return {"id": planta.id, "nombre": planta.nombre, "especie": planta.especie}


def _resumen_json(resumen, ahora):
    estado = resumen.diagnostico.estado if resumen.diagnostico else ESTADO_SIN_DATOS
    ultima = resumen.ultima_lectura
    return {
        **_planta_json(resumen.planta),
        "estado": estado,
        "estado_texto": TEXTO_ESTADO[estado],
        "recomendaciones": resumen.diagnostico.recomendaciones if resumen.diagnostico else None,
        "lectura_actual": _lectura_json(ultima) if ultima else None,
        "dispositivos": [
            {
                "codigo": d.codigo,
                "conectado": d.esta_conectado(ahora),
                "ultima_conexion": d.ultima_conexion.isoformat() if d.ultima_conexion else None,
            }
            for d in resumen.dispositivos
        ],
    }


def _lectura_json(lectura):
    return {
        "medida_en": lectura.medida_en.isoformat(),
        "humedad": lectura.humedad,
        "luz": lectura.luz,
        "temperatura": lectura.temperatura,
        "estado": lectura.estado,
        "origen": lectura.origen,
        "dispositivo": lectura.dispositivo_codigo,
    }


def _parametros_json(diagnostico):
    if diagnostico is None:
        return []
    return [
        {"nombre": p.nombre, "valor": p.valor, "unidad": p.unidad, "estado": p.estado,
         "rango_optimo": [p.rango.minimo, p.rango.maximo]}
        for p in diagnostico.parametros
    ]


def _diagnostico_json(diagnostico):
    return {
        "especie": diagnostico.especie,
        "estado": diagnostico.estado,
        "estado_texto": TEXTO_ESTADO[diagnostico.estado],
        "recomendaciones": diagnostico.recomendaciones,
        "parametros": _parametros_json(diagnostico),
    }
