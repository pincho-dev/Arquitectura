import json

import pytest

from domain.puertos import EspecieNoEncontrada
from infrastructure.especie_lookup_json import EspecieLookupJson


def _crear_json(tmp_path, contenido):
    ruta = tmp_path / "especies_test.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    return ruta


def _contenido_de_prueba():
    return {
        "potus": {
            "humedad": {"minimo": 40, "maximo": 70},
            "luz": {"minimo": 200, "maximo": 800},
            "temperatura": {"minimo": 18, "maximo": 27},
        }
    }


def test_carga_y_devuelve_los_rangos_correctos(tmp_path):
    ruta = _crear_json(tmp_path, _contenido_de_prueba())
    lookup = EspecieLookupJson(ruta)

    rangos = lookup.obtener_rangos("potus")

    assert rangos.nombre == "potus"
    assert (rangos.rango_humedad.minimo, rangos.rango_humedad.maximo) == (40, 70)
    assert (rangos.rango_luz.minimo, rangos.rango_luz.maximo) == (200, 800)
    assert (rangos.rango_temperatura.minimo, rangos.rango_temperatura.maximo) == (18, 27)


def test_normaliza_mayusculas_y_espacios(tmp_path):
    ruta = _crear_json(tmp_path, _contenido_de_prueba())
    lookup = EspecieLookupJson(ruta)

    rangos = lookup.obtener_rangos("  Potus  ")

    assert rangos.nombre == "potus"


def test_especie_no_encontrada_levanta_excepcion(tmp_path):
    ruta = _crear_json(tmp_path, _contenido_de_prueba())
    lookup = EspecieLookupJson(ruta)

    with pytest.raises(EspecieNoEncontrada):
        lookup.obtener_rangos("cactus")


def test_usa_el_archivo_de_datos_por_defecto_si_no_se_pasa_ruta():
    lookup = EspecieLookupJson()

    rangos = lookup.obtener_rangos("suculenta")

    assert rangos.nombre == "suculenta"
