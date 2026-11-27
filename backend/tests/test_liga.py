"""Reglas de la liga, casos de uso y API con dobles de prueba: sin BD."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from flask import Flask

from application.liga import ConsultarMiLiga, ConsultarRanking
from domain.liga import (
    DIVISIONES, PESO_CALIDAD, PESO_REACCION, REACCION_MAXIMA, AlcanceInvalido, Participante,
    PeriodoInvalido, ResultadoPlanta, ResultadoUsuario, armar_ranking, division_de_arranque,
    division_para, evaluar_planta, periodo_del_mes, puntos_para_subir, siguiente_division,
)
from domain.puertos import DatosLiga
from infrastructure.tokens_jwt import TokensJwt
from presentation.api_liga import crear_api_liga
from presentation.seguridad import crear_requiere_usuario
from tests.test_amistades import _RepositorioAmistadesFalso

BOGOTA = ZoneInfo("America/Bogota")
AHORA = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
NOVIEMBRE = periodo_del_mes(2026, 11, BOGOTA)
SEMILLA, BROTE, HOJA, FLOR, ARBOL = DIVISIONES


def _bogota(dia, hora=0, minuto=0, mes=11):
    return datetime(2026, mes, dia, hora, minuto, tzinfo=BOGOTA).astimezone(timezone.utc)


def _lecturas(inicio, duracion, estado, cada=timedelta(minutes=1)):
    n = int(duracion / cada)
    return [(inicio + i * cada, estado) for i in range(n)]


def _evaluar(estados, desde=NOVIEMBRE[0], hasta=AHORA):
    return evaluar_planta(1, "Potos", estados, desde, hasta, BOGOTA)


# ------------------------------------------------------------- divisiones

@pytest.mark.parametrize("puntos, division", [
    (0, SEMILLA), (39.9, SEMILLA), (40, BROTE), (59.9, BROTE), (60, HOJA),
    (74.9, HOJA), (75, FLOR), (89.9, FLOR), (90, ARBOL), (100, ARBOL),
])
def test_division_por_umbrales(puntos, division):
    assert division_para(puntos) == division


def test_al_cambiar_de_mes_se_baja_una_division_sin_pasar_de_semilla():
    assert division_de_arranque(HOJA) == BROTE
    assert division_de_arranque(SEMILLA) == SEMILLA
    assert division_de_arranque(None) == SEMILLA


def test_cuanto_falta_para_subir():
    assert puntos_para_subir(76, FLOR) == 14
    assert puntos_para_subir(95, ARBOL) is None
    assert siguiente_division(ARBOL) is None


def test_los_meses_se_cortan_a_medianoche_de_colombia():
    desde, hasta = periodo_del_mes(2026, 12, BOGOTA)

    assert desde == datetime(2026, 12, 1, 5, 0, tzinfo=timezone.utc)
    assert hasta == datetime(2027, 1, 1, 5, 0, tzinfo=timezone.utc)
    with pytest.raises(PeriodoInvalido):
        periodo_del_mes(2026, 13, BOGOTA)


# ------------------------------------------------------- puntos de planta

def test_planta_siempre_saludable_y_conectada_saca_100_y_clasifica():
    resultado = _evaluar(_lecturas(_bogota(2), timedelta(hours=25), "SALUDABLE"))

    assert resultado.puntos == 100
    assert resultado.clasifica
    assert resultado.dias_validos == 2
    assert resultado.episodios == 0


def test_en_riesgo_vale_la_mitad_y_tardar_mucho_en_recuperarla_no_da_reaccion():
    # 12 h saludable + 12 h en riesgo; se recupera a medianoche (12 h después,
    # más que REACCION_MAXIMA). Los 30 min del día siguiente no alcanzan la hora.
    estados = (_lecturas(_bogota(2), timedelta(hours=12), "SALUDABLE")
               + _lecturas(_bogota(2, 12), timedelta(hours=12), "EN_RIESGO")
               + _lecturas(_bogota(3), timedelta(minutes=30), "SALUDABLE"))

    resultado = _evaluar(estados)

    assert resultado.dias_validos == 1
    assert resultado.episodios == 1
    assert resultado.puntos == pytest.approx(PESO_CALIDAD * 0.75)
    assert resultado.clasifica


def test_reaccionar_rapido_da_casi_todos_los_puntos_de_reaccion():
    estados = (_lecturas(_bogota(2), timedelta(hours=12), "SALUDABLE")
               + _lecturas(_bogota(2, 12), timedelta(minutes=30), "CRITICO")
               + _lecturas(_bogota(2, 12, 30), timedelta(hours=11, minutes=30), "SALUDABLE"))

    resultado = _evaluar(estados)

    # 1441 min conectada (la última lectura vale 2 min, el hueco máximo), 30 de ellos en crítico.
    calidad = (1441 - 30) / 1441
    reaccion = 1 - timedelta(minutes=30) / REACCION_MAXIMA
    assert resultado.puntos == pytest.approx(round(PESO_CALIDAD * calidad + PESO_REACCION * reaccion, 1))


def test_episodio_sin_recuperar_cuenta_hasta_ahora():
    hasta = _bogota(2, 18)
    estados = (_lecturas(_bogota(2), timedelta(hours=12), "SALUDABLE")
               + _lecturas(_bogota(2, 12), timedelta(hours=6), "CRITICO"))

    resultado = _evaluar(estados, hasta=hasta)

    # 6 h sin volver a saludable = REACCION_MAXIMA: cero puntos de reacción.
    assert resultado.episodios == 1
    assert resultado.puntos == pytest.approx(PESO_CALIDAD * 12 / 18, abs=0.1)


def test_si_la_matera_deja_de_reportar_ese_rato_no_cuenta():
    estados = (_lecturas(_bogota(2), timedelta(hours=12), "SALUDABLE")
               + _lecturas(_bogota(2, 18), timedelta(hours=12), "SALUDABLE"))

    resultado = _evaluar(estados)

    # Cada bloque: 719 min entre lecturas + 2 min de la última antes del hueco.
    assert resultado.conectada == timedelta(minutes=2 * 721)


def test_menos_de_24_horas_conectada_no_clasifica_pero_tiene_puntos_provisionales():
    resultado = _evaluar(_lecturas(_bogota(2), timedelta(hours=10), "SALUDABLE"))

    assert not resultado.clasifica
    assert resultado.puntos == 100


def test_los_dias_son_de_la_zona_horaria_local_no_de_utc():
    # 23:00 a 01:00 en Bogotá es el mismo día en UTC (04:00 a 06:00).
    resultado = _evaluar(_lecturas(_bogota(2, 23), timedelta(hours=2), "SALUDABLE"))

    assert resultado.dias_validos == 2


def test_lecturas_fuera_del_periodo_se_ignoran():
    resultado = _evaluar(_lecturas(_bogota(28, mes=10), timedelta(hours=30), "CRITICO"))

    assert resultado.conectada == timedelta(0)
    assert resultado.puntos is None


# ------------------------------------------------------ usuario y ranking

def _planta(puntos, clasifica=True, planta_id=1):
    return ResultadoPlanta(planta_id, "p", puntos, clasifica, timedelta(hours=30), 2, 0)


def test_los_puntos_del_usuario_son_el_promedio_de_las_plantas_que_clasifican():
    usuario = ResultadoUsuario(1, "Ana", [_planta(90), _planta(50), _planta(10, clasifica=False)])

    assert usuario.puntos == 70
    assert usuario.puntos_provisionales == 50


def test_ranking_ordena_empata_y_deja_fuera_a_los_que_no_clasifican():
    filas = armar_ranking([
        ResultadoUsuario(1, "Ana", [_planta(80)]),
        ResultadoUsuario(2, "Beto", [_planta(95)]),
        ResultadoUsuario(3, "Caro", [_planta(80)]),
        ResultadoUsuario(4, "Dani", [_planta(100, clasifica=False)]),
        ResultadoUsuario(5, "Eli", []),
    ])

    assert [(f.posicion, f.resultado.nombre, f.division) for f in filas] == [
        (1, "Beto", ARBOL), (2, "Ana", FLOR), (2, "Caro", FLOR),
    ]


# ------------------------------------------------------------ casos de uso

class _DatosLigaFalso(DatosLiga):
    def __init__(self, participantes, estados):
        self._participantes = participantes
        self._estados = estados

    def participantes(self, usuario_ids=None):
        if usuario_ids is None:
            return [p for p in self._participantes if p.plantas]
        return [p for p in self._participantes if p.usuario_id in usuario_ids]

    def estados(self, planta_ids, desde, hasta):
        return {pid: [(t, e) for t, e in self._estados.get(pid, []) if desde <= t < hasta] for pid in planta_ids}


_SALUDABLE_NOV = _lecturas(_bogota(2), timedelta(hours=25), "SALUDABLE")
_REGULAR_NOV = (_lecturas(_bogota(2), timedelta(hours=12), "SALUDABLE")
                + _lecturas(_bogota(2, 12), timedelta(hours=12), "EN_RIESGO")
                + _lecturas(_bogota(3), timedelta(minutes=30), "SALUDABLE"))


@pytest.fixture
def datos():
    participantes = [
        Participante(1, "Ana", ((10, "Potos"),)),
        Participante(2, "Beto", ((20, "Cactus"),)),
        Participante(3, "Caro", ((30, "Helecho"),)),
        Participante(4, "Dani", ()),
    ]
    estados = {
        10: _SALUDABLE_NOV,
        20: _REGULAR_NOV,
        # Caro: en octubre le fue regular (Brote) y en noviembre aún no clasifica.
        30: [(t - timedelta(days=31), e) for t, e in _REGULAR_NOV]
            + _lecturas(_bogota(20), timedelta(hours=3), "SALUDABLE"),
    }
    return _DatosLigaFalso(participantes, estados)


def test_mi_liga_con_el_mes_impecable_queda_en_arbol(datos):
    liga = ConsultarMiLiga(datos, BOGOTA).ejecutar(1, AHORA)

    assert liga.mes == (2026, 11)
    assert liga.resultado.clasifica
    assert liga.division == ARBOL
    assert liga.siguiente_division is None
    assert liga.division_mes_anterior is None


def test_si_aun_no_clasifica_arranca_una_division_debajo_del_mes_anterior(datos):
    liga = ConsultarMiLiga(datos, BOGOTA).ejecutar(3, AHORA)

    assert not liga.resultado.clasifica
    assert liga.division_mes_anterior == BROTE
    assert liga.division == SEMILLA
    assert liga.resultado.puntos_provisionales == 100


def test_usuario_sin_plantas_queda_en_semilla(datos):
    liga = ConsultarMiLiga(datos, BOGOTA).ejecutar(4, AHORA)

    assert liga.division == SEMILLA
    assert liga.resultado.plantas == []


def test_no_se_puede_consultar_un_mes_que_no_ha_empezado(datos):
    with pytest.raises(PeriodoInvalido):
        ConsultarMiLiga(datos, BOGOTA).ejecutar(1, AHORA, 2026, 12)


def test_ranking_global_y_entre_amigos(datos):
    amistades = _RepositorioAmistadesFalso()
    amistad = amistades.crear(3, 2)
    amistades.aceptar(amistad.id, AHORA)
    ranking = ConsultarRanking(datos, amistades, BOGOTA)

    global_ = ranking.ejecutar(1, "global", AHORA)
    de_caro = ranking.ejecutar(3, "amigos", AHORA)

    assert [(f.posicion, f.resultado.nombre) for f in global_.filas] == [(1, "Ana"), (2, "Beto")]
    assert global_.mi_posicion == 1
    # Caro todavía no clasifica: ve a su amigo Beto, pero ella no tiene posición.
    assert [f.resultado.nombre for f in de_caro.filas] == ["Beto"]
    assert de_caro.mi_posicion is None


def test_alcance_desconocido_se_rechaza(datos):
    with pytest.raises(AlcanceInvalido):
        ConsultarRanking(datos, _RepositorioAmistadesFalso(), BOGOTA).ejecutar(1, "vecinos", AHORA)


# ------------------------------------------------------------------- API

@pytest.fixture
def api(datos):
    tokens = TokensJwt("s" * 40)
    app = Flask(__name__)
    app.register_blueprint(crear_api_liga(
        ConsultarMiLiga(datos, BOGOTA),
        ConsultarRanking(datos, _RepositorioAmistadesFalso(), BOGOTA),
        crear_requiere_usuario(tokens),
    ))
    return app.test_client(), {"Authorization": f"Bearer {tokens.emitir_para_usuario(1)}"}


def test_api_mi_liga(api):
    client, cabecera = api

    cuerpo = client.get("/api/liga/yo?mes=2026-11", headers=cabecera).get_json()

    assert cuerpo["mes"] == "2026-11"
    assert cuerpo["clasificado"] is True
    assert cuerpo["puntos"] == 100
    assert cuerpo["division"]["clave"] == "arbol"
    assert cuerpo["plantas"][0] == {"id": 10, "nombre": "Potos", "puntos": 100, "clasifica": True,
                                    "horas_conectada": 25.0, "dias_validos": 2, "episodios": 0}


def test_api_ranking(api):
    client, cabecera = api

    cuerpo = client.get("/api/liga/ranking?mes=2026-11&alcance=global", headers=cabecera).get_json()

    assert cuerpo["mi_posicion"] == 1
    assert cuerpo["filas"][0]["usuario"] == {"id": 1, "nombre": "Ana"}
    assert cuerpo["filas"][0]["soy_yo"] is True
    assert cuerpo["filas"][1]["division"]["nombre"] == "Brote"


def test_api_divisiones(api):
    client, cabecera = api

    cuerpo = client.get("/api/liga/divisiones", headers=cabecera).get_json()

    assert [d["nombre"] for d in cuerpo["divisiones"]] == ["Semilla", "Brote", "Hoja", "Flor", "Árbol"]
    assert cuerpo["requisitos"]["horas_minimas_mes"] == 24


@pytest.mark.parametrize("consulta, campo", [
    ("mes=noviembre", "mes"), ("mes=2026-13", "mes"), ("mes=2099-01", "mes"), ("alcance=vecinos", "alcance"),
])
def test_api_parametros_invalidos_devuelven_400(api, consulta, campo):
    client, cabecera = api

    respuesta = client.get(f"/api/liga/ranking?{consulta}", headers=cabecera)

    assert respuesta.status_code == 400
    assert respuesta.get_json()["detalle"]["campo"] == campo


def test_api_sin_token_devuelve_401(api):
    client, _ = api

    assert client.get("/api/liga/yo").status_code == 401


def test_un_episodio_sin_resolver_castiga_todos_los_dias_que_dura():
    # En riesgo de principio a fin, dos días: ningún día tiene reacción completa.
    resultado = _evaluar(_lecturas(_bogota(2), timedelta(hours=26), "EN_RIESGO"))

    assert resultado.episodios == 1
    assert resultado.puntos == pytest.approx(PESO_CALIDAD * 0.5)
