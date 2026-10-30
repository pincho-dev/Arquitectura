from datetime import datetime, timedelta, timezone

import jwt
import pytest

from infrastructure.hasher_bcrypt import HasherBcrypt
from infrastructure.tokens_jwt import ALCANCE_USUARIO, TokenInvalido, TokensJwt

SECRETO = "s" * 40


def test_token_emitido_se_verifica_y_devuelve_el_usuario():
    tokens = TokensJwt(SECRETO)

    token = tokens.emitir_para_usuario(7)

    assert tokens.verificar(token, ALCANCE_USUARIO) == 7


def test_token_bien_firmado_pero_de_otro_alcance_es_rechazado():
    otro_alcance = jwt.encode(
        {"sub": "7", "alcance": "admin", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        SECRETO, algorithm="HS256",
    )

    with pytest.raises(TokenInvalido, match="permiso"):
        TokensJwt(SECRETO).verificar(otro_alcance, ALCANCE_USUARIO)


def test_token_firmado_con_otro_secreto_es_rechazado():
    token_ajeno = TokensJwt("otro-secreto-" + "x" * 30).emitir_para_usuario(7)

    with pytest.raises(TokenInvalido):
        TokensJwt(SECRETO).verificar(token_ajeno, ALCANCE_USUARIO)


def test_token_expirado_es_rechazado():
    vencido = jwt.encode(
        {"sub": "7", "alcance": ALCANCE_USUARIO, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        SECRETO, algorithm="HS256",
    )

    with pytest.raises(TokenInvalido, match="expiró"):
        TokensJwt(SECRETO).verificar(vencido, ALCANCE_USUARIO)


def test_token_sin_firma_es_rechazado():
    sin_firma = jwt.encode({"sub": "7", "alcance": ALCANCE_USUARIO, "exp": 9999999999}, None, algorithm="none")

    with pytest.raises(TokenInvalido):
        TokensJwt(SECRETO).verificar(sin_firma, ALCANCE_USUARIO)


def test_secreto_corto_no_se_acepta():
    with pytest.raises(RuntimeError):
        TokensJwt("corto")


def test_bcrypt_verifica_solo_la_contrasena_correcta():
    hasher = HasherBcrypt()
    password_hash = hasher.hashear("secreta123")

    assert password_hash != "secreta123"
    assert hasher.verificar("secreta123", password_hash)
    assert not hasher.verificar("otra-clave", password_hash)
