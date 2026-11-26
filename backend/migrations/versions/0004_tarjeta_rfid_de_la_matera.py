"""tarjeta RFID de la matera

La fábrica cambió los stickers NFC por un lector RC522 y tarjetas RFID: cada
matera queda identificada por el UID de su tarjeta. El reclamo del usuario
sigue igual (código + clave), pero ahora llega por un QR impreso.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-26 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('dispositivos', sa.Column('rfid_uid', sa.String(length=20), nullable=True))
    op.create_unique_constraint(op.f('uq_dispositivos_rfid_uid'), 'dispositivos', ['rfid_uid'])


def downgrade() -> None:
    op.drop_constraint(op.f('uq_dispositivos_rfid_uid'), 'dispositivos', type_='unique')
    op.drop_column('dispositivos', 'rfid_uid')
