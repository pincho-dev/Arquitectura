from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError

from domain.plantas import CodigoDispositivoEnUso, Dispositivo
from domain.puertos import RepositorioDispositivos
from infrastructure.db.tablas import dispositivos
from infrastructure.tokens_dispositivo import hash_token_dispositivo


class RepositorioDispositivosBd(RepositorioDispositivos):

    def __init__(self, engine):
        self.engine = engine

    def registrar(self, codigo, planta_id, token):
        try:
            with self.engine.begin() as conexion:
                dispositivo_id = conexion.execute(
                    insert(dispositivos)
                    .values(codigo=codigo, planta_id=planta_id, token_hash=hash_token_dispositivo(token))
                    .returning(dispositivos.c.id)
                ).scalar_one()
        except IntegrityError as error:
            if getattr(error.orig.diag, "constraint_name", None) == "uq_dispositivos_codigo":
                raise CodigoDispositivoEnUso(f"Ya existe un dispositivo con el código '{codigo}'.")
            raise
        return Dispositivo(dispositivo_id, codigo, planta_id)

    def listar_de_planta(self, planta_id):
        consulta = (
            select(dispositivos.c.id, dispositivos.c.codigo, dispositivos.c.planta_id, dispositivos.c.ultima_conexion)
            .where(dispositivos.c.planta_id == planta_id, dispositivos.c.revocado_en.is_(None))
            .order_by(dispositivos.c.id)
        )
        with self.engine.connect() as conexion:
            return [Dispositivo(f.id, f.codigo, f.planta_id, f.ultima_conexion) for f in conexion.execute(consulta)]
