from application.listar_especies import ListarEspecies
from domain.modelos import RangosEspecie
from domain.valores import Rango


class _CatalogoEspeciesFalso:
    def __init__(self, especies):
        self._especies = especies

    def listar(self):
        return self._especies


def _rangos_potos():
    return RangosEspecie(
        nombre="potos",
        rango_humedad=Rango(40, 70),
        rango_luz=Rango(300, 1200),
        rango_temperatura=Rango(18, 30),
    )


def test_ejecutar_devuelve_las_especies_del_catalogo():
    especies = [_rangos_potos()]
    catalogo = _CatalogoEspeciesFalso(especies)
    caso_de_uso = ListarEspecies(catalogo)

    assert caso_de_uso.ejecutar() == especies


def test_ejecutar_devuelve_lista_vacia_si_el_catalogo_esta_vacio():
    catalogo = _CatalogoEspeciesFalso([])
    caso_de_uso = ListarEspecies(catalogo)

    assert caso_de_uso.ejecutar() == []
