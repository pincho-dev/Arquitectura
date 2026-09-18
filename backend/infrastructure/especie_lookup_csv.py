import csv
from pathlib import Path
from domain.puertos import EspecieLookup, EspecieNoEncontrada, CatalogoEspecies
from domain.modelos import RangosEspecie
from domain.valores import Rango

class EspecieLookupCsv (EspecieLookup, CatalogoEspecies):

    def __init__(self, ruta_archivo = None):
        if ruta_archivo is None:
            ruta_archivo = Path(__file__).parent / "data" / "especies.csv"

        self.datos_especies = {}
        with open(ruta_archivo, "r", encoding="utf-8", newline="") as archivo:
            for fila in csv.DictReader(archivo):
                clave = fila["especie"].strip().lower()
                self.datos_especies[clave] = fila

    def obtener_rangos(self, nombre_especie):
        clave = nombre_especie.strip().lower()
        if clave not in self.datos_especies:
            raise EspecieNoEncontrada(f"La especie '{nombre_especie}' no se encuentra en la base de datos.")
        fila = self.datos_especies[clave]
        return RangosEspecie(
            nombre = clave,
            rango_humedad = Rango(int(fila["humedad_min"]), int(fila["humedad_max"])),
            rango_temperatura = Rango(int(fila["temp_min"]), int(fila["temp_max"])),
            rango_luz = Rango(int(fila["luz_min"]), int(fila["luz_max"]))
        )
    def listar(self):
        return [self.obtener_rangos(nombre) for nombre in self.datos_especies]
