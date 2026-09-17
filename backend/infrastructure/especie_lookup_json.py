import json 
from pathlib import Path
from domain.puertos import EspecieLookup, EspecieNoEncontrada
from domain.modelos import RangosEspecie
from domain.valores import Rango

class EspecieLookupJson (EspecieLookup):

    def __init__(self, ruta_archivo = None):
        if ruta_archivo is None:
            ruta_archivo = Path(__file__).parent / "data" / "especies.json"

        with open(ruta_archivo, "r", encoding="utf-8") as archivo:
            self.datos_especies = json.load(archivo)
    def obtener_rangos(self, nombre_especie):
        clave = nombre_especie.strip().lower()
        if clave not in self.datos_especies:
            raise EspecieNoEncontrada(f"La especie '{nombre_especie}' no se encuentra en la base de datos.")
        entrada = self.datos_especies[clave]
        return RangosEspecie(
            nombre = clave,
            rango_humedad = Rango(entrada["humedad"]["minimo"], entrada["humedad"]["maximo"]),
            rango_temperatura = Rango(entrada["temperatura"]["minimo"], entrada["temperatura"]["maximo"]),
            rango_luz = Rango(entrada["luz"]["minimo"], entrada["luz"]["maximo"])
        )

