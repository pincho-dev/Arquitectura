from sqlalchemy import select

from domain.puertos import EspecieLookup, EspecieNoEncontrada, CatalogoEspecies
from domain.modelos import RangosEspecie
from domain.valores import Rango
from infrastructure.db.tablas import especies, rangos_referencia


class EspecieLookupBd(EspecieLookup, CatalogoEspecies):
    """Mismo puerto que EspecieLookupCsv, otra tecnología (R4)."""

    def __init__(self, engine):
        self.engine = engine

    def obtener_rangos(self, nombre_especie):
        clave = nombre_especie.strip().lower()
        por_especie = self._consultar(especies.c.nombre == clave)
        if clave not in por_especie:
            raise EspecieNoEncontrada(f"La especie '{nombre_especie}' no se encuentra en la base de datos.")
        return self._a_rangos(clave, por_especie[clave])

    def listar(self):
        return [self._a_rangos(nombre, rangos) for nombre, rangos in self._consultar().items()]

    def _consultar(self, *filtros):
        consulta = (
            select(especies.c.nombre, rangos_referencia.c.parametro_codigo,
                   rangos_referencia.c.minimo, rangos_referencia.c.maximo)
            .join(rangos_referencia, rangos_referencia.c.especie_id == especies.c.id)
            .where(*filtros)
            .order_by(especies.c.id)
        )
        por_especie = {}
        with self.engine.connect() as conexion:
            for fila in conexion.execute(consulta):
                por_especie.setdefault(fila.nombre, {})[fila.parametro_codigo] = Rango(fila.minimo, fila.maximo)
        return por_especie

    def _a_rangos(self, nombre, rangos):
        return RangosEspecie(
            nombre = nombre,
            rango_humedad = rangos["humedad"],
            rango_temperatura = rangos["temperatura"],
            rango_luz = rangos["luz"]
        )
