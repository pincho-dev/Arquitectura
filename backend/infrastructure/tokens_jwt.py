from datetime import datetime, timedelta, timezone

import jwt

from domain.puertos import EmisorTokens

ALCANCE_USUARIO = "usuario"


class TokenInvalido(Exception):
    pass


class TokensJwt(EmisorTokens):
    """Emite y verifica JWT firmados con HMAC-SHA256 y el secreto del servidor.

    Cada token lleva un "alcance" que se exige al verificar. Los dispositivos
    NO usan JWT: tienen su propio token opaco, revocable, guardado como hash
    en la BD (ver infrastructure/tokens_dispositivo.py), así que un token de
    dispositivo nunca pasa esta verificación y viceversa (R7).
    """

    ALGORITMO = "HS256"

    def __init__(self, secreto, minutos_validez=60):
        if not secreto or len(secreto) < 32:
            raise RuntimeError("JWT_SECRET falta o es demasiado corto (mínimo 32 caracteres).")
        self.secreto = secreto
        self.minutos_validez = minutos_validez

    def emitir_para_usuario(self, usuario_id):
        ahora = datetime.now(timezone.utc)
        payload = {
            "sub": str(usuario_id),
            "alcance": ALCANCE_USUARIO,
            "iat": ahora,
            "exp": ahora + timedelta(minutes=self.minutos_validez),
        }
        return jwt.encode(payload, self.secreto, algorithm=self.ALGORITMO)

    def verificar(self, token, alcance):
        """Devuelve el id (sub) del token si es válido y del alcance pedido."""
        try:
            payload = jwt.decode(
                token, self.secreto, algorithms=[self.ALGORITMO],
                options={"require": ["sub", "exp", "alcance"]},
            )
        except jwt.ExpiredSignatureError:
            raise TokenInvalido("El token expiró.")
        except jwt.InvalidTokenError:
            raise TokenInvalido("El token no es válido.")

        if payload["alcance"] != alcance:
            raise TokenInvalido("El token no tiene permiso para esta operación.")
        return int(payload["sub"])
