import csv

import pytest

from domain.puertos import EspecieNoEncontrada
from infrastructure.especie_lookup_csv import EspecieLookupCsv


CAMPOS = ["especie", "humedad_min", "humedad_max", "luz_min", "luz_max", "temp_min", "temp_max"]


def _crear_csv(tmp_path, filas):
    ruta = tmp_path / "especies_test.csv"
    with open(ruta, "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=CAMPOS)
        escritor.writeheader()
        escritor.writerows(filas)
    return ruta


def _fila_de_prueba(especie="potus", humedad=(40, 70), luz=(200, 800), temperatura=(18, 27)):
    return {
        "especie": especie,
        "humedad_min": humedad[0],
        "humedad_max": humedad[1],
        "luz_min": luz[0],
        "luz_max": luz[1],
        "temp_min": temperatura[0],
        "temp_max": temperatura[1],
    }


def test_carga_y_devuelve_los_rangos_correctos(tmp_path):
    ruta = _crear_csv(tmp_path, [_fila_de_prueba()])
    lookup = EspecieLookupCsv(ruta)

    rangos = lookup.obtener_rangos("potus")

    assert rangos.nombre == "potus"
    assert (rangos.rango_humedad.minimo, rangos.rango_humedad.maximo) == (40, 70)
    assert (rangos.rango_luz.minimo, rangos.rango_luz.maximo) == (200, 800)
    assert (rangos.rango_temperatura.minimo, rangos.rango_temperatura.maximo) == (18, 27)


def test_normaliza_mayusculas_y_espacios(tmp_path):
    ruta = _crear_csv(tmp_path, [_fila_de_prueba()])
    lookup = EspecieLookupCsv(ruta)

    rangos = lookup.obtener_rangos("  Potus  ")

    assert rangos.nombre == "potus"


def test_especie_no_encontrada_levanta_excepcion(tmp_path):
    ruta = _crear_csv(tmp_path, [_fila_de_prueba()])
    lookup = EspecieLookupCsv(ruta)

    with pytest.raises(EspecieNoEncontrada):
        lookup.obtener_rangos("cactus")


def test_usa_el_archivo_de_datos_por_defecto_si_no_se_pasa_ruta():
    lookup = EspecieLookupCsv()

    rangos = lookup.obtener_rangos("suculenta")

    assert rangos.nombre == "suculenta"


def test_listar_devuelve_los_rangos_de_todas_las_especies(tmp_path):
    filas = [
        _fila_de_prueba("potus", (40, 70), (200, 800), (18, 27)),
        _fila_de_prueba("suculenta", (10, 30), (500, 1200), (15, 32)),
    ]
    ruta = _crear_csv(tmp_path, filas)
    lookup = EspecieLookupCsv(ruta)

    especies = lookup.listar()

    assert {rangos.nombre for rangos in especies} == {"potus", "suculenta"}


def test_listar_devuelve_lista_vacia_si_no_hay_especies(tmp_path):
    ruta = _crear_csv(tmp_path, [])
    lookup = EspecieLookupCsv(ruta)

    assert lookup.listar() == []
