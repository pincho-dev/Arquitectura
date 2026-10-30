"""Adaptador de dispositivos con dobles de prueba: sin servidor real ni BD."""
from datetime import datetime, timedelta, timezone

import pytest
from flask import Flask

from application.diagnosticar_planta import DiagnosticarPlanta
from application.registrar_lectura import RegistrarLectura
from domain.plantas import Dispositivo
from presentation.api_dispositivos import crear_api_dispositivos
from tests.test_plantas import DUENA, _EspecieLookupFalso, _HistorialFalso, _RepositorioPlantasFalso

TOKEN = "dev_token_valido"


class _AutenticadorFalso:
    def __init__(self, dispositivo):
        self.dispositivo = dispositivo

    def autenticar(self, token):
        return self.dispositivo if token == TOKEN else None


@pytest.fixture
def entorno():
    plantas, historial = _RepositorioPlantasFalso(), _HistorialFalso()
    planta = plantas.crear("Potos sala", "potos", DUENA)
    registrar = RegistrarLectura(plantas, historial, DiagnosticarPlanta(_EspecieLookupFalso()))
    app = Flask(__name__)
    app.register_blueprint(crear_api_dispositivos(registrar, _AutenticadorFalso(Dispositivo(9, "ESP32-01", planta.id))))
    return app.test_client(), historial


def _lectura(**cambios):
    cuerpo = {"dispositivo": "ESP32-01", "medida_en": datetime.now(timezone.utc).isoformat(),
              "humedad": 55, "luz": 500, "temperatura": 22}
    cuerpo.update(cambios)
    return cuerpo


def _post(client, cuerpo, codigo="ESP32-01", token=TOKEN):
    return client.post(f"/api/dispositivos/{codigo}/lecturas", json=cuerpo,
                       headers={"Authorization": f"Bearer {token}"} if token else {})


def test_lectura_valida_se_registra(entorno):
    client, historial = entorno

    respuesta = _post(client, _lectura())

    assert respuesta.status_code == 201
    assert respuesta.get_json()["estado"] == "SALUDABLE"
    assert historial.lecturas[0].origen == "dispositivo"


def test_lectura_fuera_de_rango_se_registra_con_estado_critico(entorno):
    client, historial = entorno

    respuesta = _post(client, _lectura(humedad=10))

    assert respuesta.status_code == 201
    assert respuesta.get_json()["estado"] == "CRITICO"


@pytest.mark.parametrize("cambios, campo", [
    ({"humedad": "sensor-error"}, "humedad"),
    ({"humedad": True}, "humedad"),
    ({"medida_en": "ayer a las 3"}, "medida_en"),
    ({"medida_en": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()}, "medida_en"),
    ({"dispositivo": "ESP32-99"}, "dispositivo"),
])
def test_datos_invalidos_devuelven_400_y_no_se_guardan(entorno, cambios, campo):
    client, historial = entorno

    respuesta = _post(client, _lectura(**cambios))

    assert respuesta.status_code == 400
    assert respuesta.get_json()["detalle"]["campo"] == campo
    assert historial.lecturas == []


def test_valor_fisicamente_imposible_devuelve_400(entorno):
    client, historial = entorno

    assert _post(client, _lectura(humedad=140)).status_code == 400
    assert historial.lecturas == []


def test_reenvio_de_la_misma_lectura_devuelve_409(entorno):
    client, _ = entorno
    cuerpo = _lectura()
    _post(client, cuerpo)

    respuesta = _post(client, cuerpo)

    assert respuesta.status_code == 409


@pytest.mark.parametrize("token", [None, "dev_token_falso", "eyJ.jwt.de-usuario"])
def test_sin_token_de_dispositivo_valido_devuelve_401(entorno, token):
    client, _ = entorno

    assert _post(client, _lectura(), token=token).status_code == 401


def test_token_de_otro_dispositivo_en_la_url_devuelve_403(entorno):
    client, _ = entorno

    assert _post(client, _lectura(), codigo="ESP32-02").status_code == 403
