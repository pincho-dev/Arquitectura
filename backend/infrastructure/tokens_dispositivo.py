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

    def generar_clave_reclamo(self):
        # Va impresa en el sticker NFC: más corta que el token, pero con 72
        # bits de azar sigue siendo imposible de adivinar.
        return secrets.token_urlsafe(9)


def hash_secreto(token):
    # Para tokens de dispositivo y claves de reclamo. SHA-256 basta (no
    # bcrypt): son aleatorios y largos, no hay diccionario que probar, y el
    # token se verifica en cada lectura del dispositivo.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
