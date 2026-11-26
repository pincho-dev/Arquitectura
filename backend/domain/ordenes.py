"""Órdenes que el dueño le puede mandar a su matera en vivo (por el WebSocket
del ESP32). No sabe nada de WebSocket: solo qué órdenes existen y con qué
parámetros."""


class OrdenInvalida(ValueError):
    pass


class DispositivoDesconectado(Exception):
    pass


# Mientras la matera no tenga bomba, "regar" solo enciende el LED en el
# firmware; el contrato ya queda listo para cuando se conecte el actuador.
ORDENES_PERMITIDAS = {
    "parpadear": {},                   # identificar físicamente la matera
    "reportar": {},                    # mandar una lectura ya mismo
    "regar": {"segundos": (1, 30)},    # activar la bomba N segundos
}


class Orden:
    def __init__(self, nombre, parametros=None):
        parametros = {} if parametros is None else parametros
        if nombre not in ORDENES_PERMITIDAS:
            permitidas = ", ".join(sorted(ORDENES_PERMITIDAS))
            raise OrdenInvalida(f"Orden '{nombre}' no reconocida. Permitidas: {permitidas}.")
        if not isinstance(parametros, dict):
            raise OrdenInvalida("Los parámetros de la orden deben ser un objeto.")

        esperados = ORDENES_PERMITIDAS[nombre]
        sobrantes = set(parametros) - set(esperados)
        if sobrantes:
            raise OrdenInvalida(f"La orden '{nombre}' no acepta: {', '.join(sorted(sobrantes))}.")

        limpios = {}
        for campo, (minimo, maximo) in esperados.items():
            if campo not in parametros:
                raise OrdenInvalida(f"La orden '{nombre}' requiere '{campo}'.")
            valor = parametros[campo]
            if isinstance(valor, bool) or not isinstance(valor, int) or not minimo <= valor <= maximo:
                raise OrdenInvalida(f"'{campo}' debe ser un entero entre {minimo} y {maximo}.")
            limpios[campo] = valor

        self.nombre = nombre
        self.parametros = limpios
