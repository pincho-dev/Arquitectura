


class ValorFueraDeRangoFisico(Exception):
    pass

class Medicion:
    def __init__(self , especie, humedad, luz, temperatura):
        if humedad < 0 or humedad > 100:
            raise ValorFueraDeRangoFisico("La humedad debe estar entre 0 y 100.")
        if luz < 0:
            raise ValorFueraDeRangoFisico("La luz no puede ser negativa.")
        if temperatura < -30 or temperatura > 60:
            raise ValorFueraDeRangoFisico("La temperatura debe estar entre -30 y 60.")
        self.especie = especie
        self.humedad = humedad
        self.luz = luz
        self.temperatura = temperatura

class RangosEspecie:
    def __init__(self, nombre, rango_humedad, rango_luz, rango_temperatura):
        self.nombre = nombre
        self.rango_humedad = rango_humedad
        self.rango_luz = rango_luz
        self.rango_temperatura = rango_temperatura

class ParametroEvaluado:
    def __init__(self, nombre, valor, unidad, rango, estado):
        self.nombre = nombre
        self.valor = valor
        self.unidad = unidad
        self.rango = rango
        self.estado = estado

class Diagnostico:
    def __init__(self, especie, estado, parametros, recomendaciones):
        self.especie = especie
        self.estado = estado
        self.parametros = parametros
        self.recomendaciones = recomendaciones

