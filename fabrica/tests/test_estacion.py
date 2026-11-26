import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import estacion  # noqa: E402
from cliente_api import ErrorApi  # noqa: E402
from estacion import ErrorDeEtiqueta, fabricar_una  # noqa: E402
from etiqueta import clave_de, qr_en_terminal  # noqa: E402
from lector_rfid import LectorRfidSimulado  # noqa: E402

CONFIG = {"host": "192.168.1.50", "puerto": 5000, "ssid": "MiWifi", "clave": 'con"comillas'}
URL = "http://192.168.1.50:5500/reclamar.html?codigo=MAT-0001&clave=k3y"


class _ApiFalsa:
    def __init__(self):
        self.descartadas = []
        self.pedidas = []

    def fabricar(self, especie, codigo=None, rfid_uid=None):
        self.pedidas.append(rfid_uid)
        return {"codigo": codigo or "MAT-0001", "especie": especie, "token_firmware": "dev_abc",
                "rfid_uid": rfid_uid, "url_reclamo": URL}

    def descartar(self, codigo):
        self.descartadas.append(codigo)


def _fabricar(api, lector, tmp_path):
    return fabricar_una(api, lector, "potos", tmp_path / "salida", CONFIG,
                        carpeta_materas=tmp_path / "materas", avisar=lambda _: None)


def test_lee_la_tarjeta_registra_la_matera_y_genera_etiqueta_y_firmware(tmp_path):
    api, lector = _ApiFalsa(), LectorRfidSimulado()
    matera, etiqueta, archivo = _fabricar(api, lector, tmp_path)

    assert api.pedidas == lector.leidos            # el UID leído es el que se manda al backend
    assert etiqueta.name == "MAT-0001_etiqueta.png" and etiqueta.stat().st_size > 0
    contenido = archivo.read_text()
    assert '#define TOKEN_MATERA     "dev_abc"' in contenido
    assert '#define CODIGO_MATERA    "MAT-0001"' in contenido
    assert '#define SERVIDOR_HOST    "192.168.1.50"' in contenido
    assert r'#define WIFI_CLAVE       "con\"comillas"' in contenido
    assert (tmp_path / "materas" / "MAT-0001.json").exists()
    registro = (tmp_path / "salida" / "registro_fabricacion.csv").read_text()
    assert "rfid_uid" in registro and lector.leidos[0] in registro


def test_sin_lector_rfid_la_matera_sale_solo_con_qr(tmp_path):
    api = _ApiFalsa()
    matera, etiqueta, _ = _fabricar(api, None, tmp_path)
    assert api.pedidas == [None]
    assert matera["rfid_uid"] is None and etiqueta.exists()


def test_si_falla_la_etiqueta_se_descarta_la_matera(tmp_path, monkeypatch):
    def _falla(*_):
        raise OSError("disco lleno")
    monkeypatch.setattr(estacion, "generar_etiqueta", _falla)
    api = _ApiFalsa()

    with pytest.raises(ErrorDeEtiqueta):
        _fabricar(api, LectorRfidSimulado(), tmp_path)
    assert api.descartadas == ["MAT-0001"]
    assert not (tmp_path / "salida" / "MAT-0001.h").exists()


def test_tarjeta_repetida_no_deja_nada_que_deshacer(tmp_path):
    class _ApiConTarjetaUsada(_ApiFalsa):
        def fabricar(self, especie, codigo=None, rfid_uid=None):
            raise ErrorApi("La tarjeta RFID ya está pegada a otra matera.", 409, "TARJETA_RFID_EN_USO")

    api = _ApiConTarjetaUsada()
    with pytest.raises(ErrorApi):
        _fabricar(api, LectorRfidSimulado(), tmp_path)
    assert api.descartadas == []
    assert not (tmp_path / "salida").exists()


def test_qr_lleva_la_url_de_reclamo():
    assert clave_de(URL) == "k3y"
    assert len(qr_en_terminal(URL).splitlines()) > 10
