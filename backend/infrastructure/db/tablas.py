"""
Esquema de la base de datos (SQLAlchemy Core).

Vive en infraestructura: el dominio no sabe que existen tablas. Las
migraciones de Alembic (backend/migrations) crean exactamente este esquema;
`alembic check` falla si se desalinean.
"""
from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column, DateTime, ForeignKey, Identity,
    Index, Integer, MetaData, Numeric, String, Table, UniqueConstraint, func, text,
)

metadata = MetaData(naming_convention={
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
})


def _medida():
    # Float de Python al leer (asdecimal=False): el dominio opera con float.
    return Numeric(8, 2, asdecimal=False)


def _creado_en():
    return Column("creado_en", DateTime(timezone=True), nullable=False, server_default=func.now())


# ---------------------------------------------------------------- usuarios

usuarios = Table(
    "usuarios", metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("nombre", String(100), nullable=False),
    Column("email", String(255), nullable=False),
    Column("password_hash", String(255), nullable=False),
    Column("activo", Boolean, nullable=False, server_default=text("true")),
    _creado_en(),
    CheckConstraint("email = lower(email)", name="email_minusculas"),
    UniqueConstraint("email"),
)

roles = Table(
    "roles", metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("nombre", String(50), nullable=False, unique=True),
)

usuario_roles = Table(
    "usuario_roles", metadata,
    Column("usuario_id", BigInteger, ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True),
    Column("rol_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Index(None, "rol_id"),
)

# Se guarda el SHA-256 del refresh token, nunca el token en claro.
refresh_tokens = Table(
    "refresh_tokens", metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("usuario_id", BigInteger, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
    Column("token_hash", String(64), nullable=False, unique=True),
    Column("expira_en", DateTime(timezone=True), nullable=False),
    Column("revocado_en", DateTime(timezone=True)),
    _creado_en(),
    Index(None, "usuario_id"),
)

# ------------------------------------------------- tabla de referencia (R4)

# Catálogo de variables medibles. Agregar una (ej. pH) es insertar una fila,
# no alterar tablas.
parametros = Table(
    "parametros", metadata,
    Column("codigo", String(20), primary_key=True),
    Column("nombre", String(50), nullable=False),
    Column("unidad", String(10), nullable=False),
)

especies = Table(
    "especies", metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("nombre", String(50), nullable=False, unique=True),
    Column("nombre_cientifico", String(100)),
    CheckConstraint("nombre = lower(nombre)", name="nombre_minusculas"),
)

rangos_referencia = Table(
    "rangos_referencia", metadata,
    Column("especie_id", Integer, ForeignKey("especies.id", ondelete="CASCADE"), primary_key=True),
    Column("parametro_codigo", String(20), ForeignKey("parametros.codigo"), primary_key=True),
    Column("minimo", _medida(), nullable=False),
    Column("maximo", _medida(), nullable=False),
    CheckConstraint("minimo <= maximo", name="minimo_menor_maximo"),
)

# ---------------------------------------------------- plantas y dispositivos

plantas = Table(
    "plantas", metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("nombre", String(100), nullable=False),
    Column("especie_id", Integer, ForeignKey("especies.id"), nullable=False),
    _creado_en(),
    Index(None, "especie_id"),
)

# Dueños de cada planta (muchos a muchos, decisión de la sesión 2026-09-30).
usuario_planta = Table(
    "usuario_planta", metadata,
    Column("usuario_id", BigInteger, ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True),
    Column("planta_id", BigInteger, ForeignKey("plantas.id", ondelete="CASCADE"), primary_key=True),
    Index(None, "planta_id"),
)

# Cada dispositivo (matera) reporta lecturas de UNA planta; su token solo sirve
# para eso. Una matera recién fabricada no tiene planta (planta_id NULL) hasta
# que un usuario la reclama con la clave de su sticker NFC; mientras tanto sus
# lecturas se rechazan.
dispositivos = Table(
    "dispositivos", metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("codigo", String(50), nullable=False, unique=True),
    Column("planta_id", BigInteger, ForeignKey("plantas.id", ondelete="CASCADE")),
    Column("token_hash", String(64), nullable=False, unique=True),
    # Especie del kit con que se vendió la matera: la planta se crea con ella al reclamarla.
    Column("especie_id", Integer, ForeignKey("especies.id")),
    Column("clave_reclamo_hash", String(64)),
    Column("reclamado_en", DateTime(timezone=True)),
    Column("revocado_en", DateTime(timezone=True)),
    Column("ultima_conexion", DateTime(timezone=True)),
    _creado_en(),
    CheckConstraint("planta_id IS NOT NULL OR clave_reclamo_hash IS NOT NULL", name="reclamable_o_con_planta"),
    Index(None, "planta_id"),
)

# ------------------------------------------------------------ historial (R5)

lecturas = Table(
    "lecturas", metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("planta_id", BigInteger, ForeignKey("plantas.id", ondelete="CASCADE"), nullable=False),
    Column("origen", String(15), nullable=False),
    # Los dispositivos se revocan (revocado_en), no se borran: así el historial conserva su origen.
    Column("dispositivo_id", BigInteger, ForeignKey("dispositivos.id")),
    Column("humedad", _medida(), nullable=False),
    Column("luz", _medida(), nullable=False),
    Column("temperatura", _medida(), nullable=False),
    Column("estado", String(15), nullable=False),
    Column("medida_en", DateTime(timezone=True), nullable=False),
    Column("recibida_en", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("origen IN ('formulario', 'dispositivo')", name="origen_valido"),
    CheckConstraint("origen = 'formulario' OR dispositivo_id IS NOT NULL", name="dispositivo_si_origen_dispositivo"),
    CheckConstraint("estado IN ('SALUDABLE', 'EN_RIESGO', 'CRITICO')", name="estado_valido"),
    CheckConstraint("humedad BETWEEN 0 AND 100", name="humedad_fisica"),
    CheckConstraint("luz >= 0", name="luz_fisica"),
    CheckConstraint("temperatura BETWEEN -30 AND 60", name="temperatura_fisica"),
    # Un ESP32 que reintenta el mismo envío no duplica la lectura.
    UniqueConstraint("dispositivo_id", "medida_en"),
    # "Última lectura" e historial de una planta salen de este índice.
    Index("ix_lecturas_planta_id_medida_en", "planta_id", text("medida_en DESC")),
)
