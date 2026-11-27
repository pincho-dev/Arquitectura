"""galería de fotos

Para presumir la planta: cada foto va ligada a una planta, con una copia de
su última lectura al subirla. El archivo (ya sin EXIF) vive fuera de la BD,
en el AlmacenFotos; aquí solo queda su clave.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-26 22:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'fotos',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column('planta_id', sa.BigInteger(), nullable=False),
        sa.Column('autor_id', sa.BigInteger(), nullable=False),
        sa.Column('clave_archivo', sa.String(length=32), nullable=False),
        sa.Column('tipo', sa.String(length=30), nullable=False),
        sa.Column('ancho', sa.Integer(), nullable=False),
        sa.Column('alto', sa.Integer(), nullable=False),
        sa.Column('descripcion', sa.String(length=280), nullable=True),
        sa.Column('estado', sa.String(length=15), nullable=True),
        sa.Column('humedad', sa.Numeric(precision=8, scale=2, asdecimal=False), nullable=True),
        sa.Column('luz', sa.Numeric(precision=8, scale=2, asdecimal=False), nullable=True),
        sa.Column('temperatura', sa.Numeric(precision=8, scale=2, asdecimal=False), nullable=True),
        sa.Column('medida_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("estado IS NULL OR estado IN ('SALUDABLE', 'EN_RIESGO', 'CRITICO')", name=op.f('ck_fotos_estado_valido')),
        sa.ForeignKeyConstraint(['planta_id'], ['plantas.id'], name=op.f('fk_fotos_planta_id_plantas'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['autor_id'], ['usuarios.id'], name=op.f('fk_fotos_autor_id_usuarios'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_fotos')),
        sa.UniqueConstraint('clave_archivo', name=op.f('uq_fotos_clave_archivo')),
    )
    op.create_index(op.f('ix_fotos_planta_id'), 'fotos', ['planta_id'], unique=False)
    op.create_index(op.f('ix_fotos_autor_id'), 'fotos', ['autor_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_fotos_autor_id'), table_name='fotos')
    op.drop_index(op.f('ix_fotos_planta_id'), table_name='fotos')
    op.drop_table('fotos')
