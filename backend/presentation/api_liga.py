"""Adaptador de entrada REST de la gamificación: divisiones, mi liga, ranking
(global o entre amigos) y amistades. Todas las rutas exigen JWT de usuario."""
import re

from flask import Blueprint, g, jsonify, request

from domain.amistades import AmigoNoRegistrado, AmistadNoEncontrada, SolicitudInvalida, SolicitudYaExiste, YaSonAmigos
from domain.liga import (
    ALCANCE_GLOBAL, DIVISIONES, MINIMO_CONECTADA_DIA, MINIMO_CONECTADA_MES, AlcanceInvalido, PeriodoInvalido,
)
from presentation.http import ErrorDeEntrada, ahora_utc, error_json, leer_objeto, leer_texto

_FORMATO_MES = re.compile(r"^(\d{4})-(\d{2})$")


def crear_api_liga(consultar_mi_liga, consultar_ranking, requiere_usuario):
    api = Blueprint("liga", __name__, url_prefix="/api/liga")

    @api.errorhandler(ErrorDeEntrada)
    def _entrada_invalida(e):
        return error_json("PARAMETRO_INVALIDO", str(e), 400, campo=e.campo)

    @api.errorhandler(PeriodoInvalido)
    def _periodo_invalido(e):
        return error_json("PARAMETRO_INVALIDO", str(e), 400, campo="mes")

    @api.errorhandler(AlcanceInvalido)
    def _alcance_invalido(e):
        return error_json("PARAMETRO_INVALIDO", str(e), 400, campo="alcance")

    @api.route("/divisiones", methods=["GET"])
    @requiere_usuario
    def divisiones():
        return jsonify({
            "divisiones": [_division_json(d) for d in DIVISIONES],
            "requisitos": _requisitos_json(),
        })

    @api.route("/yo", methods=["GET"])
    @requiere_usuario
    def yo():
        anio, mes = _leer_mes(request.args.get("mes"))
        liga = consultar_mi_liga.ejecutar(g.usuario_id, ahora_utc(), anio, mes)
        r = liga.resultado
        return jsonify({
            "mes": _mes_texto(liga.mes),
            "clasificado": r.clasifica,
            "puntos": r.puntos,
            "puntos_provisionales": r.puntos_provisionales,
            "division": _division_json(liga.division),
            "division_mes_anterior": _division_json(liga.division_mes_anterior),
            "siguiente_division": _division_json(liga.siguiente_division),
            "puntos_para_subir": liga.puntos_para_subir,
            "requisitos": _requisitos_json(),
            "plantas": [_planta_json(p) for p in r.plantas],
        })

    @api.route("/ranking", methods=["GET"])
    @requiere_usuario
    def ranking():
        anio, mes = _leer_mes(request.args.get("mes"))
        alcance = request.args.get("alcance", ALCANCE_GLOBAL)
        resultado = consultar_ranking.ejecutar(g.usuario_id, alcance, ahora_utc(), anio, mes)
        return jsonify({
            "mes": _mes_texto(resultado.mes),
            "alcance": resultado.alcance,
            "mi_posicion": resultado.mi_posicion,
            "filas": [
                {
                    "posicion": f.posicion,
                    "usuario": {"id": f.resultado.usuario_id, "nombre": f.resultado.nombre},
                    "puntos": f.resultado.puntos,
                    "division": _division_json(f.division),
                    "plantas": sum(1 for p in f.resultado.plantas if p.clasifica),
                    "soy_yo": f.resultado.usuario_id == g.usuario_id,
                }
                for f in resultado.filas
            ],
        })

    return api


def crear_api_amigos(listar_amistades, solicitar_amistad, aceptar_amistad, eliminar_amistad, requiere_usuario):
    api = Blueprint("amigos", __name__, url_prefix="/api/amigos")

    @api.errorhandler(ErrorDeEntrada)
    def _entrada_invalida(e):
        return error_json("PARAMETRO_INVALIDO", str(e), 400, campo=e.campo)

    @api.errorhandler(SolicitudInvalida)
    def _solicitud_invalida(e):
        return error_json("PARAMETRO_INVALIDO", str(e), 400, campo="correo")

    @api.errorhandler(AmigoNoRegistrado)
    def _no_registrado(e):
        return error_json("USUARIO_NO_ENCONTRADO", str(e), 404, campo="correo")

    @api.errorhandler(AmistadNoEncontrada)
    def _no_encontrada(e):
        return error_json("AMISTAD_NO_ENCONTRADA", str(e), 404)

    @api.errorhandler(SolicitudYaExiste)
    def _ya_existe(e):
        return error_json("SOLICITUD_YA_ENVIADA", str(e), 409, campo="correo")

    @api.errorhandler(YaSonAmigos)
    def _ya_amigos(e):
        return error_json("YA_SON_AMIGOS", str(e), 409, campo="correo")

    @api.route("", methods=["GET"])
    @requiere_usuario
    def listar():
        return jsonify([_amistad_json(a, g.usuario_id) for a in listar_amistades.ejecutar(g.usuario_id)])

    @api.route("", methods=["POST"])
    @requiere_usuario
    def solicitar():
        datos = leer_objeto(request.get_json(silent=True))
        amistad = solicitar_amistad.ejecutar(g.usuario_id, leer_texto(datos, "correo"), ahora_utc())
        # 201 si se creó la solicitud; 200 si se aceptó una que ya te habían enviado.
        return jsonify(_amistad_json(amistad, g.usuario_id)), 200 if amistad.aceptada else 201

    @api.route("/<int:amistad_id>/aceptar", methods=["POST"])
    @requiere_usuario
    def aceptar(amistad_id):
        amistad = aceptar_amistad.ejecutar(g.usuario_id, amistad_id, ahora_utc())
        return jsonify(_amistad_json(amistad, g.usuario_id))

    @api.route("/<int:amistad_id>", methods=["DELETE"])
    @requiere_usuario
    def eliminar(amistad_id):
        eliminar_amistad.ejecutar(g.usuario_id, amistad_id)
        return "", 204

    return api


def _leer_mes(texto):
    """'2026-11' -> (2026, 11). Sin parámetro: (None, None), el mes actual."""
    if texto is None:
        return None, None
    coincidencia = _FORMATO_MES.match(texto)
    if not coincidencia:
        raise ErrorDeEntrada("El parámetro 'mes' debe tener el formato AAAA-MM (ej. 2026-11).", campo="mes")
    return int(coincidencia.group(1)), int(coincidencia.group(2))


def _mes_texto(mes):
    return f"{mes[0]:04d}-{mes[1]:02d}"


def _division_json(division):
    if division is None:
        return None
    return {"clave": division.clave, "nombre": division.nombre, "metal": division.metal,
            "minimo": division.minimo, "maximo": division.maximo}


def _requisitos_json():
    return {
        "horas_minimas_mes": MINIMO_CONECTADA_MES.total_seconds() / 3600,
        "horas_minimas_dia": MINIMO_CONECTADA_DIA.total_seconds() / 3600,
    }


def _planta_json(resultado):
    return {
        "id": resultado.planta_id,
        "nombre": resultado.nombre,
        "puntos": resultado.puntos,
        "clasifica": resultado.clasifica,
        "horas_conectada": round(resultado.conectada.total_seconds() / 3600, 1),
        "dias_validos": resultado.dias_validos,
        "episodios": resultado.episodios,
    }


def _amistad_json(amistad, usuario_id):
    otro_id, otro_nombre = amistad.otro(usuario_id)
    return {
        "id": amistad.id,
        "usuario": {"id": otro_id, "nombre": otro_nombre},
        "estado": amistad.estado_para(usuario_id),
        "creada_en": amistad.creada_en.isoformat() if amistad.creada_en else None,
        "aceptada_en": amistad.aceptada_en.isoformat() if amistad.aceptada_en else None,
    }
