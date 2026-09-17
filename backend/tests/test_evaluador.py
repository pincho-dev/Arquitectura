from domain.evaluador import EvaluadorDiagnostico
from domain.modelos import Medicion, RangosEspecie
from domain.valores import Rango


def _rangos(humedad=(30, 70), luz=(200, 800), temperatura=(15, 30)):
    return RangosEspecie(
        nombre="especie_test",
        rango_humedad=Rango(*humedad),
        rango_luz=Rango(*luz),
        rango_temperatura=Rango(*temperatura),
    )


def _evaluar(humedad, luz, temperatura, rangos=None):
    medicion = Medicion(especie="especie_test", humedad=humedad, luz=luz, temperatura=temperatura)
    return EvaluadorDiagnostico().Evaluar(medicion, rangos or _rangos())


def test_todo_dentro_de_rango_es_saludable():
    diagnostico = _evaluar(humedad=50, luz=500, temperatura=20)

    assert diagnostico.estado == "SALUDABLE"
    assert all(p.estado == "OPTIMO" for p in diagnostico.parametros)


def test_desviacion_leve_no_cuenta_como_fuera_de_rango():
    # humedad=75 sobre un máximo de 70 -> 7.14% de desviación, por debajo del umbral leve (10%)
    diagnostico = _evaluar(humedad=75, luz=500, temperatura=20)

    assert diagnostico.estado == "SALUDABLE"
    humedad = next(p for p in diagnostico.parametros if p.nombre == "Humedad")
    assert humedad.estado == "OPTIMO"


def test_un_parametro_bajo_da_en_riesgo():
    # humedad=24 bajo un mínimo de 30 -> 20% de desviación (BAJO, no severo)
    diagnostico = _evaluar(humedad=24, luz=500, temperatura=20)

    assert diagnostico.estado == "EN_RIESGO"
    humedad = next(p for p in diagnostico.parametros if p.nombre == "Humedad")
    assert humedad.estado == "BAJO"


def test_un_parametro_alto_da_en_riesgo():
    # luz=900 sobre un máximo de 800 -> 12.5% de desviación (ALTO, no severo)
    diagnostico = _evaluar(humedad=50, luz=900, temperatura=20)

    assert diagnostico.estado == "EN_RIESGO"
    luz = next(p for p in diagnostico.parametros if p.nombre == "Luz")
    assert luz.estado == "ALTO"


def test_dos_parametros_fuera_de_rango_da_critico_por_conteo():
    # humedad 20% bajo, luz 12.5% alto: ninguno severo, pero son 2 -> CRITICO
    diagnostico = _evaluar(humedad=24, luz=900, temperatura=20)

    assert diagnostico.estado == "CRITICO"


def test_un_parametro_severo_dispara_critico_solo():
    # temperatura=45 sobre un máximo de 30 -> 50% de desviación (severo)
    diagnostico = _evaluar(humedad=50, luz=500, temperatura=45)

    assert diagnostico.estado == "CRITICO"
    temperatura = next(p for p in diagnostico.parametros if p.nombre == "Temperatura")
    assert temperatura.estado == "ALTO"


def test_desviacion_severa_por_debajo_tambien_dispara_critico():
    # humedad=10 bajo un mínimo de 30 -> 66.7% de desviación (severo, por debajo)
    diagnostico = _evaluar(humedad=10, luz=500, temperatura=20)

    assert diagnostico.estado == "CRITICO"
    humedad = next(p for p in diagnostico.parametros if p.nombre == "Humedad")
    assert humedad.estado == "BAJO"


def test_rango_con_minimo_negativo_clasifica_bajo_no_alto():
    # temperatura=-15 bajo un rango de -10 a 25 -> debe seguir siendo BAJO, no ALTO
    rangos = _rangos(temperatura=(-10, 25))
    diagnostico = _evaluar(humedad=50, luz=500, temperatura=-15, rangos=rangos)

    temperatura = next(p for p in diagnostico.parametros if p.nombre == "Temperatura")
    assert temperatura.estado == "BAJO"


def test_rango_con_minimo_cero_no_divide_por_cero():
    # temperatura=-3 bajo un rango de 0 a 25 -> debe usar el ancho del rango, no crashear
    rangos = _rangos(temperatura=(0, 25))
    diagnostico = _evaluar(humedad=50, luz=500, temperatura=-3, rangos=rangos)

    temperatura = next(p for p in diagnostico.parametros if p.nombre == "Temperatura")
    assert temperatura.estado == "BAJO"
    assert diagnostico.estado == "EN_RIESGO"


def test_unidades_correctas_por_parametro():
    diagnostico = _evaluar(humedad=50, luz=500, temperatura=20)

    unidades = {p.nombre: p.unidad for p in diagnostico.parametros}
    assert unidades == {"Humedad": "%", "Luz": "lux", "Temperatura": "C"}
