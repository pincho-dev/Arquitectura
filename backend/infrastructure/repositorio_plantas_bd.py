from sqlalchemy import delete, func, insert, select
from sqlalchemy.dialects.postgresql import insert as insert_pg

from domain.plantas import Planta
from domain.puertos import EspecieNoEncontrada, RepositorioPlantas
from infrastructure.db.tablas import especies, plantas, usuario_planta


class RepositorioPlantasBd(RepositorioPlantas):

    def __init__(self, engine):
        self.engine = engine

    def crear(self, nombre, especie, usuario_id):
        with self.engine.begin() as conexion:
            especie_id = conexion.execute(
                select(especies.c.id).where(especies.c.nombre == especie)
            ).scalar_one_or_none()
            if especie_id is None:
                raise EspecieNoEncontrada(f"La especie '{especie}' no se encuentra en la base de datos.")
            planta_id = conexion.execute(
                insert(plantas).values(nombre=nombre, especie_id=especie_id).returning(plantas.c.id)
            ).scalar_one()
            conexion.execute(insert(usuario_planta).values(usuario_id=usuario_id, planta_id=planta_id))
        return Planta(planta_id, nombre, especie, {usuario_id})

    def buscar(self, planta_id):
        filas = self._consultar(plantas.c.id == planta_id)
        return filas[0] if filas else None

    def listar_de_usuario(self, usuario_id):
        de_usuario = select(usuario_planta.c.planta_id).where(usuario_planta.c.usuario_id == usuario_id)
        return self._consultar(plantas.c.id.in_(de_usuario))

    def eliminar(self, planta_id):
        with self.engine.begin() as conexion:
            conexion.execute(delete(plantas).where(plantas.c.id == planta_id))

    def agregar_dueno(self, planta_id, usuario_id):
        # ON CONFLICT DO NOTHING: compartir dos veces con la misma persona no falla.
        with self.engine.begin() as conexion:
            conexion.execute(
                insert_pg(usuario_planta)
                .values(usuario_id=usuario_id, planta_id=planta_id)
                .on_conflict_do_nothing()
            )

    def _consultar(self, filtro):
        consulta = (
            select(plantas.c.id, plantas.c.nombre, especies.c.nombre.label("especie"),
                   func.array_agg(usuario_planta.c.usuario_id).label("duenos"))
            .join(especies, especies.c.id == plantas.c.especie_id)
            .join(usuario_planta, usuario_planta.c.planta_id == plantas.c.id)
            .where(filtro)
            .group_by(plantas.c.id, especies.c.nombre)
            .order_by(plantas.c.id)
        )
        with self.engine.connect() as conexion:
            return [Planta(f.id, f.nombre, f.especie, f.duenos) for f in conexion.execute(consulta)]
