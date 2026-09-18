
from domain.evaluador import EvaluadorDiagnostico
from domain.modelos import Medicion

class DiagnosticarPlanta:

    def __init__ (self, especie_lookup):
        self.especie_lookup = especie_lookup

    def ejecutar(self, especie, humedad, luz, temperatura):
        medicion = Medicion(especie, humedad, luz, temperatura)
        rangos = self.especie_lookup.obtener_rangos(especie)
        evaluador = EvaluadorDiagnostico()
        return evaluador.Evaluar(medicion, rangos)