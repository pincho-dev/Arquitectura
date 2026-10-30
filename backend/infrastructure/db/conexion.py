import os

from sqlalchemy import create_engine


def crear_engine(url=None):
    url = url or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Falta DATABASE_URL en el entorno (.env).")
    return create_engine(url, pool_pre_ping=True)
