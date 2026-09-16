from backend.domain.modelos import Diagnostico, ParametroEvaluado
from backend.domain.valores import EstadoPlanta

class EvaluadorDiagnostico:

    Recomendaciones_por_Estado={
                    EstadoPlanta.SALUDABLE: "La planta se encuentra en buen estado. Mantener las condiciones actuales.",
                    EstadoPlanta.EN_RIESGO: "La planta presenta signos de estrés. Ajustar las condiciones de humedad, luz o temperatura según sea necesario.",
                    EstadoPlanta.CRITICO: "La planta está en estado crítico. Tomar medidas inmediatas para corregir las condiciones ambientales y considerar la intervención de un especialista en plantas."
                }

    def Evaluar(self, medicion, rangos):
        parametros_evaluados = []
        hay_severo = False
        contador_fuera_de_rango = 0
        

        for nombre, valor, rango, unidad in [
            ("Humedad", medicion.humedad, rangos.rango_humedad, "%"),
            ("Luz", medicion.luz, rangos.rango_luz, "lux"),
            ("Temperatura", medicion.temperatura, rangos.rango_temperatura, "C")
        ]:
            derivacion_pct = self._calcular_derivacion(valor, rango)
            estado = self._clasificar_parametro(derivacion_pct)

            if abs(derivacion_pct) >= 0.5:
                hay_severo = True
            if estado != "OPTIMO":
                contador_fuera_de_rango += 1

            parametros_evaluados.append(ParametroEvaluado(nombre, valor, unidad, rango, estado))

        if hay_severo:
            estado_global = "CRITICO"
        elif contador_fuera_de_rango >= 2:
            estado_global = "CRITICO"
        elif contador_fuera_de_rango == 1:
            estado_global = "EN_RIESGO"
        else:  
            estado_global = "SALUDABLE"

        recomendaciones = self.Recomendaciones_por_Estado.get(EstadoPlanta(estado_global), "Recomendación no disponible.")
        return Diagnostico(medicion.especie, estado_global, parametros_evaluados, recomendaciones)

    def _calcular_derivacion(self, valor, rango):
        if valor < rango.minimo:
            limite = abs(rango.minimo if rango.minimo != 0 else (rango.maximo - rango.minimo))
            return -((rango.minimo - valor) / limite)
        elif valor > rango.maximo:
            limite = abs(rango.maximo if rango.maximo != 0 else (rango.maximo - rango.minimo))
            return (valor - rango.maximo) / limite
        else:
            return 0

    def _clasificar_parametro(self, derivacion_pct):

        magnitud = abs(derivacion_pct)
        if magnitud <= 0.1:
            return "OPTIMO"
        elif derivacion_pct < 0:
            return "BAJO"
        else:
            return "ALTO"
            