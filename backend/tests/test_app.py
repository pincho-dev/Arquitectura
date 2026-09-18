import pytest

from presentation.app import app


@pytest.fixture
def client():
    return app.test_client()


def test_especies_devuelve_el_catalogo_completo(client):
    respuesta = client.get("/especies")

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    nombres = {especie["nombre"] for especie in cuerpo}
    assert nombres == {"sansevieria", "potos", "suculenta", "helecho", "lavanda"}
    assert set(cuerpo[0]["rangos"].keys()) == {"humedad", "luz", "temperatura"}


def test_diagnostico_devuelve_estado_para_especie_valida(client):
    respuesta = client.post(
        "/diagnostico",
        json={"especie": "potos", "humedad": 55, "luz": 500, "temperatura": 22},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["especie"] == "potos"
    assert cuerpo["estado"] in {"SALUDABLE", "EN_RIESGO", "CRITICO"}
    assert len(cuerpo["parametros"]) == 3


def test_diagnostico_especie_no_encontrada_devuelve_404(client):
    respuesta = client.post(
        "/diagnostico",
        json={"especie": "cactus", "humedad": 55, "luz": 500, "temperatura": 22},
    )

    assert respuesta.status_code == 404
    assert respuesta.get_json()["error"] == "ESPECIE_NO_SOPORTADA"


def test_diagnostico_valor_fuera_de_rango_fisico_devuelve_400(client):
    respuesta = client.post(
        "/diagnostico",
        json={"especie": "potos", "humedad": 150, "luz": 500, "temperatura": 22},
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == "PARAMETRO_INVALIDO"


def test_diagnostico_parametro_ausente_devuelve_400(client):
    respuesta = client.post(
        "/diagnostico",
        json={"especie": "potos", "humedad": 55, "luz": 500},
    )

    assert respuesta.status_code == 400
    cuerpo = respuesta.get_json()
    assert cuerpo["error"] == "PARAMETRO_INVALIDO"
    assert cuerpo["detalle"]["campo"] == "temperatura"


def test_diagnostico_valor_no_numerico_devuelve_400(client):
    respuesta = client.post(
        "/diagnostico",
        json={"especie": "potos", "humedad": "alta", "luz": 500, "temperatura": 22},
    )

    assert respuesta.status_code == 400
    cuerpo = respuesta.get_json()
    assert cuerpo["error"] == "PARAMETRO_INVALIDO"
    assert cuerpo["detalle"]["campo"] == "humedad"


def test_diagnostico_cuerpo_no_json_devuelve_400(client):
    respuesta = client.post(
        "/diagnostico",
        data="esto no es json",
        content_type="text/plain",
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == "PARAMETRO_INVALIDO"


def test_estado_reporta_especies_cargadas_y_registra_solicitudes(client):
    client.get("/especies")

    respuesta = client.get("/estado")

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["activo"] is True
    assert cuerpo["especies_cargadas"] == 5
    assert any(s["ruta"] == "/especies" for s in cuerpo["solicitudes_recientes"])


def test_estado_no_se_registra_a_si_mismo(client):
    client.get("/estado")

    respuesta = client.get("/estado")
    cuerpo = respuesta.get_json()

    assert all(s["ruta"] != "/estado" for s in cuerpo["solicitudes_recientes"])
