import hashlib
import secrets

from domain.puertos import GeneradorTokensDispositivo

PREFIJO = "dev_"


class GeneradorTokensDispositivoAleatorio(GeneradorTokensDispositivo):
    """Token opaco de 192 bits. No es JWT a propósito: un ESP32 no puede
    renovar tokens, así que el suyo es de larga duración y debe poder
    revocarse en la BD en cualquier momento."""

    def generar(self):
        return PREFIJO + secrets.token_urlsafe(24)


def hash_token_dispositivo(token):
    # SHA-256 basta (no bcrypt): el token ya es aleatorio y largo, no hay
    # diccionario que probar, y se verifica en cada lectura del dispositivo.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
