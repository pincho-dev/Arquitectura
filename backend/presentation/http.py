"""Utilidades de borde compartidas por los adaptadores REST: cuerpo de error
uniforme y traducción del JSON de entrada a tipos de Python (RA6: el request
crudo nunca llega a los casos de uso)."""
from datetime import datetime, timedelta, timezone

from flask import jsonify

CAMPOS_MEDICION = ("humedad", "luz", "temperatura")
# Tolerancia para relojes de dispositivos algo adelantados.
MARGEN_FUTURO = timedelta(minutes=5)


class ErrorDeEntrada(Exception):
    def __init__(self, mensaje, campo=None):
        super().__init__(mensaje)
        self.campo = campo


def error_json(codigo, mensaje, status, campo=None):
    return jsonify({"error": codigo, "mensaje": mensaje, "detalle": {"campo": campo}}), status


def leer_objeto(datos):
    if not isinstance(datos, dict):
        raise ErrorDeEntrada("El cuerpo de la petición debe ser un objeto JSON.")
    return datos


def leer_texto(datos, campo):
    valor = datos.get(campo)
    if not isinstance(valor, str) or not valor.strip():
        raise ErrorDeEntrada(f"Falta el parámetro '{campo}' o no es texto.", campo=campo)
    return valor


def leer_medicion(datos):
    valores = {}
    for campo in CAMPOS_MEDICION:
        if campo not in datos:
            raise ErrorDeEntrada(f"Falta el parámetro '{campo}'.", campo=campo)
        valor = datos[campo]
        # bool es subclase de int en Python: True no es una humedad válida.
        if isinstance(valor, bool) or not isinstance(valor, (int, float, str)):
            raise ErrorDeEntrada(f"El parámetro '{campo}' debe ser numérico.", campo=campo)
        try:
            valores[campo] = float(valor)
        except ValueError:
            raise ErrorDeEntrada(f"El parámetro '{campo}' debe ser numérico.", campo=campo)
        if valores[campo] != valores[campo] or valores[campo] in (float("inf"), float("-inf")):
            raise ErrorDeEntrada(f"El parámetro '{campo}' debe ser un número finito.", campo=campo)
    return valores


def leer_fecha(datos, campo, ahora):
    """Marca de tiempo ISO 8601. Sin zona horaria se asume UTC."""
    texto = datos.get(campo)
    if not isinstance(texto, str):
        raise ErrorDeEntrada(f"Falta el parámetro '{campo}' (fecha ISO 8601).", campo=campo)
    try:
        fecha = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        raise ErrorDeEntrada(f"El parámetro '{campo}' no es una fecha ISO 8601 válida.", campo=campo)
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    if fecha > ahora + MARGEN_FUTURO:
        raise ErrorDeEntrada(f"El parámetro '{campo}' está en el futuro.", campo=campo)
    return fecha


def ahora_utc():
    return datetime.now(timezone.utc)
