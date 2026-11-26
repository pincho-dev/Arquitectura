"""API de la estación de fábrica, descarte de materas y la regla de
"conectado" combinando WebSocket y HTTP."""
from datetime import datetime, timedelta, timezone

import pytest
from flask import Flask

from application.materas import DescartarMatera, FabricarMatera, ReclamarMatera
from domain.plantas import Dispositivo, MateraYaReclamada
from presentation.api_fabrica import crear_api_fabrica
from tests.test_plantas import DUENA, _GeneradorFalso, _RepositorioDispositivosFalso, _RepositorioPlantasFalso

CLAVE = "clave-de-la-fabrica"
AHORA = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def fabrica():
    dispositivos, plantas = _RepositorioDispositivosFalso(), _RepositorioPlantasFalso()
    app = Flask(__name__)
    app.register_blueprint(crear_api_fabrica(
        FabricarMatera(dispositivos, _GeneradorFalso()), DescartarMatera(dispositivos), CLAVE, "http://192.168.1.50:5500/",
    ))
    return app.test_client(), dispositivos, ReclamarMatera(dispositivos, plantas)


def _post(cliente, cuerpo, clave=CLAVE):
    return cliente.post("/api/fabrica/materas", json=cuerpo, headers={"X-Fabrica-Clave": clave})


def test_fabrica_exige_su_clave(fabrica):
    cliente, _, _ = fabrica
    assert _post(cliente, {"especie": "potos"}, clave="otra").status_code == 401
    assert cliente.post("/api/fabrica/materas", json={"especie": "potos"}).status_code == 401


def test_fabrica_deshabilitada_sin_clave_configurada():
    app = Flask(__name__)
    app.register_blueprint(crear_api_fabrica(None, None, "", "http://x"))
    respuesta = app.test_client().post("/api/fabrica/materas", json={}, headers={"X-Fabrica-Clave": ""})
    assert respuesta.status_code == 503


def test_fabrica_entrega_token_y_url_del_sticker(fabrica):
    cliente, dispositivos, _ = fabrica
    respuesta = _post(cliente, {"especie": "potos", "codigo": "mat-0001"})
    assert respuesta.status_code == 201
    cuerpo = respuesta.get_json()
    assert cuerpo["codigo"] == "MAT-0001"
    assert cuerpo["token_firmware"] == "dev_token_de_prueba"
    assert cuerpo["url_sticker_nfc"] == "http://192.168.1.50:5500/reclamar.html?codigo=MAT-0001&clave=clave-sticker"
    assert dispositivos.buscar_por_codigo("MAT-0001").planta_id is None


def test_fabrica_genera_codigo_si_no_se_da_y_valida_especie(fabrica):
    cliente, _, _ = fabrica
    assert _post(cliente, {"especie": "potos"}).get_json()["codigo"].startswith("MAT-")
    assert _post(cliente, {"especie": "cactus"}).status_code == 404
    assert _post(cliente, {}).status_code == 400


def test_descartar_solo_materas_sin_reclamar(fabrica):
    cliente, dispositivos, reclamar = fabrica
    _post(cliente, {"especie": "potos", "codigo": "MAT-A"})
    _post(cliente, {"especie": "potos", "codigo": "MAT-B"})
    reclamar.ejecutar(DUENA, "MAT-B", "clave-sticker")

    assert cliente.delete("/api/fabrica/materas/mat-a", headers={"X-Fabrica-Clave": CLAVE}).status_code == 204
    assert dispositivos.buscar_por_codigo("MAT-A") is None
    respuesta = cliente.delete("/api/fabrica/materas/MAT-B", headers={"X-Fabrica-Clave": CLAVE})
    assert respuesta.status_code == 409
    assert dispositivos.buscar_por_codigo("MAT-B") is not None


def test_descartar_matera_inexistente():
    with pytest.raises(MateraYaReclamada):
        DescartarMatera(_RepositorioDispositivosFalso()).ejecutar("MAT-NADA")


# ------------------------------------------------------------ presencia

def _dispositivo(hace_segundos):
    ultima = None if hace_segundos is None else AHORA - timedelta(seconds=hace_segundos)
    return Dispositivo(1, "MAT-1", 1, ultima)


def test_sin_websocket_se_usa_la_ventana_del_ultimo_reporte_http():
    assert _dispositivo(30).esta_conectado(AHORA) is True
    assert _dispositivo(600).esta_conectado(AHORA) is False
    assert _dispositivo(None).esta_conectado(AHORA) is False


def test_con_websocket_abierto_esta_conectada_aunque_no_haya_reportado():
    assert _dispositivo(600).esta_conectado(AHORA, (True, None)) is True


def test_al_cerrar_el_websocket_queda_desconectada_al_instante():
    # Reportó hace 5 s, pero cerró el WebSocket hace 2 s: ya no está.
    cerro = AHORA - timedelta(seconds=2)
    assert _dispositivo(5).esta_conectado(AHORA, (False, cerro)) is False


def test_si_despues_de_cerrar_el_websocket_reporta_por_http_vuelve_a_estar_conectada():
    cerro = AHORA - timedelta(seconds=60)
    assert _dispositivo(5).esta_conectado(AHORA, (False, cerro)) is True
