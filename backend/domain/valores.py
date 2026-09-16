from enum import Enum

class EstadoParametro(Enum):
    BAJO = "BAJO"
    OPTIMO = "OPTIMO"
    ALTO = "ALTO"

class EstadoPlanta(Enum):
    SALUDABLE = "SALUDABLE"
    EN_RIESGO = "EN_RIESGO"
    CRITICO = "CRITICO"

class Rango():
    def __init__(self, minimo, maximo):
        if minimo > maximo:
            raise ValueError("El valor mínimo no puede ser mayor que el valor máximo.")
        self.minimo = minimo
        self.maximo = maximo
        
    def clasificar(self, valor):
        if valor < self.minimo:
            return EstadoParametro.BAJO
        elif valor > self.maximo:
            return EstadoParametro.ALTO
        else:
            return EstadoParametro.OPTIMO
        
