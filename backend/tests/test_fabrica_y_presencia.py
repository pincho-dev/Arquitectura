"""API de la estación de fábrica, descarte de materas y la regla de
"conectado" combinando WebSocket y HTTP."""
from datetime import datetime, timedelta, timezone

import pytest
from flask import Flask

from application.materas import DescartarMatera, FabricarMatera, IdentificarMatera, ReclamarMatera
from domain.plantas import DatosDePlantaInvalidos, Dispositivo, MateraYaReclamada, normalizar_uid_rfid
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
        identificar_matera=IdentificarMatera(dispositivos),
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


def test_fabrica_entrega_token_url_del_qr_y_guarda_la_tarjeta(fabrica):
    cliente, dispositivos, _ = fabrica
    respuesta = _post(cliente, {"especie": "potos", "codigo": "mat-0001", "rfid_uid": "04:a1:b2:c3"})
    assert respuesta.status_code == 201
    cuerpo = respuesta.get_json()
    assert cuerpo["codigo"] == "MAT-0001"
    assert cuerpo["rfid_uid"] == "04A1B2C3"
    assert cuerpo["token_firmware"] == "dev_token_de_prueba"
    assert cuerpo["url_reclamo"] == "http://192.168.1.50:5500/reclamar.html?codigo=MAT-0001&clave=clave-sticker"
    assert dispositivos.buscar_por_codigo("MAT-0001").planta_id is None


def test_fabrica_sin_tarjeta_sigue_funcionando(fabrica):
    cliente, _, _ = fabrica
    cuerpo = _post(cliente, {"especie": "potos"}).get_json()
    assert cuerpo["rfid_uid"] is None


def test_la_misma_tarjeta_no_se_puede_pegar_a_dos_materas(fabrica):
    cliente, _, _ = fabrica
    assert _post(cliente, {"especie": "potos", "rfid_uid": "04A1B2C3"}).status_code == 201
    respuesta = _post(cliente, {"especie": "potos", "rfid_uid": "04 a1 b2 c3"})
    assert respuesta.status_code == 409
    assert respuesta.get_json()["error"] == "TARJETA_RFID_EN_USO"


@pytest.mark.parametrize("uid", ["xyz", "04A1B2", "04A1B2C3D4", 1234])
def test_uid_rfid_invalido_se_rechaza(fabrica, uid):
    cliente, _, _ = fabrica
    assert _post(cliente, {"especie": "potos", "rfid_uid": uid}).status_code == 400


def test_normalizar_uid_rfid_acepta_4_7_y_10_bytes():
    assert normalizar_uid_rfid("de:ad:be:ef") == "DEADBEEF"
    assert normalizar_uid_rfid("04-11-22-33-44-55-66") == "04112233445566"
    assert len(normalizar_uid_rfid("0" * 20)) == 20
    with pytest.raises(DatosDePlantaInvalidos):
        normalizar_uid_rfid("")


def test_identificar_matera_por_su_tarjeta(fabrica):
    cliente, _, reclamar = fabrica
    _post(cliente, {"especie": "potos", "codigo": "MAT-A", "rfid_uid": "04A1B2C3"})
    cabecera = {"X-Fabrica-Clave": CLAVE}

    cuerpo = cliente.get("/api/fabrica/materas/rfid/04a1b2c3", headers=cabecera).get_json()
    assert cuerpo == {"codigo": "MAT-A", "especie": "potos", "rfid_uid": "04A1B2C3", "reclamada": False}

    reclamar.ejecutar(DUENA, "MAT-A", "clave-sticker")
    assert cliente.get("/api/fabrica/materas/rfid/04A1B2C3", headers=cabecera).get_json()["reclamada"] is True
    respuesta = cliente.get("/api/fabrica/materas/rfid/DEADBEEF", headers=cabecera)
    assert respuesta.status_code == 404
    assert respuesta.get_json()["error"] == "TARJETA_RFID_DESCONOCIDA"
    assert cliente.get("/api/fabrica/materas/rfid/04A1B2C3").status_code == 401


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
