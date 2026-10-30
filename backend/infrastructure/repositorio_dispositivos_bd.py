from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import IntegrityError

from domain.plantas import CodigoDispositivoEnUso, Dispositivo
from domain.puertos import EspecieNoEncontrada, RepositorioDispositivos
from infrastructure.db.tablas import dispositivos, especies
from infrastructure.tokens_dispositivo import hash_secreto


class RepositorioDispositivosBd(RepositorioDispositivos):

    def __init__(self, engine):
        self.engine = engine

    def registrar(self, codigo, planta_id, token):
        return self._insertar(codigo, planta_id=planta_id, token_hash=hash_secreto(token))

    def registrar_de_fabrica(self, codigo, especie, token, clave_reclamo):
        with self.engine.connect() as conexion:
            especie_id = conexion.execute(
                select(especies.c.id).where(especies.c.nombre == especie)
            ).scalar_one_or_none()
        if especie_id is None:
            raise EspecieNoEncontrada(f"La especie '{especie}' no se encuentra en la base de datos.")
        dispositivo = self._insertar(
            codigo, token_hash=hash_secreto(token), especie_id=especie_id,
            clave_reclamo_hash=hash_secreto(clave_reclamo),
        )
        dispositivo.especie = especie
        return dispositivo

    def buscar_para_reclamo(self, codigo, clave_reclamo):
        consulta = (
            select(dispositivos.c.id, dispositivos.c.codigo, dispositivos.c.planta_id,
                   dispositivos.c.ultima_conexion, especies.c.nombre.label("especie"))
            .outerjoin(especies, especies.c.id == dispositivos.c.especie_id)
            .where(dispositivos.c.codigo == codigo,
                   dispositivos.c.clave_reclamo_hash == hash_secreto(clave_reclamo),
                   dispositivos.c.revocado_en.is_(None))
        )
        with self.engine.connect() as conexion:
            f = conexion.execute(consulta).first()
        return Dispositivo(f.id, f.codigo, f.planta_id, f.ultima_conexion, f.especie) if f else None

    def asignar_planta(self, dispositivo_id, planta_id):
        # El WHERE planta_id IS NULL hace el reclamo atómico: si dos usuarios
        # tocan el sticker a la vez, solo uno actualiza la fila.
        with self.engine.begin() as conexion:
            resultado = conexion.execute(
                update(dispositivos)
                .where(dispositivos.c.id == dispositivo_id, dispositivos.c.planta_id.is_(None))
                .values(planta_id=planta_id, reclamado_en=func.now())
            )
        return resultado.rowcount == 1

    def listar_de_planta(self, planta_id):
        consulta = (
            select(dispositivos.c.id, dispositivos.c.codigo, dispositivos.c.planta_id, dispositivos.c.ultima_conexion)
            .where(dispositivos.c.planta_id == planta_id, dispositivos.c.revocado_en.is_(None))
            .order_by(dispositivos.c.id)
        )
        with self.engine.connect() as conexion:
            return [Dispositivo(f.id, f.codigo, f.planta_id, f.ultima_conexion) for f in conexion.execute(consulta)]

    def _insertar(self, codigo, **valores):
        try:
            with self.engine.begin() as conexion:
                dispositivo_id = conexion.execute(
                    insert(dispositivos).values(codigo=codigo, **valores).returning(dispositivos.c.id)
                ).scalar_one()
        except IntegrityError as error:
            if getattr(error.orig.diag, "constraint_name", None) == "uq_dispositivos_codigo":
                raise CodigoDispositivoEnUso(f"Ya existe un dispositivo con el código '{codigo}'.")
            raise
        return Dispositivo(dispositivo_id, codigo, valores.get("planta_id"))
