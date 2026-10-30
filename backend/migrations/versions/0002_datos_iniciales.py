"""Datos iniciales: parámetros, especies y rangos (desde el CSV del Anexo B) y roles.

Se lee infrastructure/data/especies.csv para que CSV y BD tengan siempre
los mismos rangos de referencia: una sola fuente citable.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-29
"""
import csv
from pathlib import Path

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

RUTA_CSV = Path(__file__).resolve().parents[2] / "infrastructure" / "data" / "especies.csv"

# codigo del parámetro -> (nombre, unidad, columnas min/max en el CSV)
PARAMETROS = {
    "humedad": ("Humedad", "%", "humedad_min", "humedad_max"),
    "luz": ("Luz", "lux", "luz_min", "luz_max"),
    "temperatura": ("Temperatura", "C", "temp_min", "temp_max"),
}


def upgrade():
    conexion = op.get_bind()

    conexion.execute(
        sa.text("INSERT INTO parametros (codigo, nombre, unidad) VALUES (:codigo, :nombre, :unidad)"),
        [{"codigo": c, "nombre": n, "unidad": u} for c, (n, u, _, _) in PARAMETROS.items()],
    )

    with open(RUTA_CSV, encoding="utf-8", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            especie_id = conexion.execute(
                sa.text("INSERT INTO especies (nombre) VALUES (:nombre) RETURNING id"),
                {"nombre": fila["especie"].strip().lower()},
            ).scalar_one()
            conexion.execute(
                sa.text(
                    "INSERT INTO rangos_referencia (especie_id, parametro_codigo, minimo, maximo) "
                    "VALUES (:especie_id, :codigo, :minimo, :maximo)"
                ),
                [
                    {"especie_id": especie_id, "codigo": codigo,
                     "minimo": float(fila[col_min]), "maximo": float(fila[col_max])}
                    for codigo, (_, _, col_min, col_max) in PARAMETROS.items()
                ],
            )

    conexion.execute(
        sa.text("INSERT INTO roles (nombre) VALUES (:nombre)"),
        [{"nombre": "usuario"}, {"nombre": "admin"}],
    )


def downgrade():
    for tabla in ("roles", "rangos_referencia", "especies", "parametros"):
        op.execute(f"DELETE FROM {tabla}")
