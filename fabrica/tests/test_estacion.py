import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cliente_api import ErrorApi  # noqa: E402
from estacion import fabricar_una  # noqa: E402
from lector_nfc import ErrorDeGrabacion, LectorNfcSimulado  # noqa: E402

CONFIG = {"host": "192.168.1.50", "puerto": 5000, "ssid": "MiWifi", "clave": 'con"comillas'}


class _ApiFalsa:
    def __init__(self):
        self.descartadas = []

    def fabricar(self, especie, codigo=None):
        return {"codigo": codigo or "MAT-0001", "especie": especie, "token_firmware": "dev_abc",
                "url_sticker_nfc": "http://192.168.1.50:5500/reclamar.html?codigo=MAT-0001&clave=k"}

    def descartar(self, codigo):
        self.descartadas.append(codigo)


class _LectorQueFalla(LectorNfcSimulado):
    def grabar_url(self, url):
        raise ErrorDeGrabacion("se movió el sticker")


def test_graba_la_url_del_sticker_y_genera_el_config_del_firmware(tmp_path):
    api, lector = _ApiFalsa(), LectorNfcSimulado()
    matera, uid, archivo = fabricar_una(api, lector, "potos", tmp_path / "salida", CONFIG,
                                        carpeta_materas=tmp_path / "materas", avisar=lambda _: None)
    assert lector.grabados == [(uid, matera["url_sticker_nfc"])]
    contenido = archivo.read_text()
    assert '#define TOKEN_MATERA     "dev_abc"' in contenido
    assert '#define CODIGO_MATERA    "MAT-0001"' in contenido
    assert '#define SERVIDOR_HOST    "192.168.1.50"' in contenido
    assert r'#define WIFI_CLAVE       "con\"comillas"' in contenido
    assert (tmp_path / "materas" / "MAT-0001.json").exists()
    assert "MAT-0001" in (tmp_path / "salida" / "registro_fabricacion.csv").read_text()


def test_si_falla_la_grabacion_se_descarta_la_matera(tmp_path):
    api = _ApiFalsa()
    with pytest.raises(ErrorDeGrabacion):
        fabricar_una(api, _LectorQueFalla(), "potos", tmp_path, CONFIG,
                     carpeta_materas=tmp_path / "materas", avisar=lambda _: None)
    assert api.descartadas == ["MAT-0001"]
    assert not (tmp_path / "MAT-0001.h").exists()


def test_error_del_backend_no_toca_el_sticker(tmp_path):
    class _ApiCaida(_ApiFalsa):
        def fabricar(self, especie, codigo=None):
            raise ErrorApi("especie no soportada", 404)

    lector = LectorNfcSimulado()
    with pytest.raises(ErrorApi):
        fabricar_una(_ApiCaida(), lector, "cactus", tmp_path, CONFIG, carpeta_materas=tmp_path, avisar=lambda _: None)
    assert lector.grabados == []
