"""amistades para la liga

El ranking de la gamificación es global o entre amigos. Para el de amigos
hace falta saber quién es amigo de quién: una solicitud que el otro acepta.
Los puntos no se guardan: se calculan desde la tabla de lecturas.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-26 18:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'amistades',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column('solicitante_id', sa.BigInteger(), nullable=False),
        sa.Column('destinatario_id', sa.BigInteger(), nullable=False),
        sa.Column('aceptada_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('solicitante_id <> destinatario_id', name=op.f('ck_amistades_no_a_si_mismo')),
        sa.ForeignKeyConstraint(['solicitante_id'], ['usuarios.id'], name=op.f('fk_amistades_solicitante_id_usuarios'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['destinatario_id'], ['usuarios.id'], name=op.f('fk_amistades_destinatario_id_usuarios'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_amistades')),
    )
    op.create_index(op.f('ix_amistades_destinatario_id'), 'amistades', ['destinatario_id'], unique=False)
    op.create_index(
        'uq_amistades_par', 'amistades',
        [sa.text('least(solicitante_id, destinatario_id)'), sa.text('greatest(solicitante_id, destinatario_id)')],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('uq_amistades_par', table_name='amistades')
    op.drop_index(op.f('ix_amistades_destinatario_id'), table_name='amistades')
    op.drop_table('amistades')
