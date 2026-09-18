import pytest

from application.diagnosticar_planta import DiagnosticarPlanta
from domain.modelos import RangosEspecie, ValorFueraDeRangoFisico
from domain.puertos import EspecieLookup, EspecieNoEncontrada
from domain.valores import Rango


class _EspecieLookupFalso(EspecieLookup):
    def __init__(self, rangos_por_especie):
        self._rangos_por_especie = rangos_por_especie

    def obtener_rangos(self, nombre_especie):
        if nombre_especie not in self._rangos_por_especie:
            raise EspecieNoEncontrada(nombre_especie)
        return self._rangos_por_especie[nombre_especie]


def _rangos_potus():
    return RangosEspecie(
        nombre="potus",
        rango_humedad=Rango(40, 70),
        rango_luz=Rango(200, 800),
        rango_temperatura=Rango(18, 27),
    )


def test_ejecutar_devuelve_diagnostico_saludable_con_todo_en_rango():
    lookup = _EspecieLookupFalso({"potus": _rangos_potus()})
    caso_de_uso = DiagnosticarPlanta(lookup)

    diagnostico = caso_de_uso.ejecutar(especie="potus", humedad=55, luz=500, temperatura=22)

    assert diagnostico.estado == "SALUDABLE"
    assert diagnostico.especie == "potus"


def test_ejecutar_propaga_especie_no_encontrada():
    lookup = _EspecieLookupFalso({"potus": _rangos_potus()})
    caso_de_uso = DiagnosticarPlanta(lookup)

    with pytest.raises(EspecieNoEncontrada):
        caso_de_uso.ejecutar(especie="cactus", humedad=55, luz=500, temperatura=22)


def test_ejecutar_propaga_valor_fuera_de_rango_fisico():
    lookup = _EspecieLookupFalso({"potus": _rangos_potus()})
    caso_de_uso = DiagnosticarPlanta(lookup)

    with pytest.raises(ValorFueraDeRangoFisico):
        caso_de_uso.ejecutar(especie="potus", humedad=150, luz=500, temperatura=22)


def test_ejecutar_usa_los_rangos_de_la_especie_pedida():
    rangos_suculenta = RangosEspecie(
        nombre="suculenta",
        rango_humedad=Rango(10, 30),
        rango_luz=Rango(500, 1200),
        rango_temperatura=Rango(15, 32),
    )
    lookup = _EspecieLookupFalso({"potus": _rangos_potus(), "suculenta": rangos_suculenta})
    caso_de_uso = DiagnosticarPlanta(lookup)

    # humedad=50 está fuera del rango de suculenta (10-30) pero dentro del de potus (40-70)
    diagnostico = caso_de_uso.ejecutar(especie="suculenta", humedad=50, luz=800, temperatura=20)

    humedad = next(p for p in diagnostico.parametros if p.nombre == "Humedad")
    assert humedad.estado == "ALTO"
