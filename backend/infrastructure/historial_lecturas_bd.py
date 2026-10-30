from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError

from domain.plantas import Lectura, LecturaDuplicada
from domain.puertos import HistorialLecturas
from infrastructure.db.tablas import dispositivos, lecturas


class HistorialLecturasBd(HistorialLecturas):

    def __init__(self, engine):
        self.engine = engine

    def guardar(self, lectura):
        try:
            with self.engine.begin() as conexion:
                conexion.execute(insert(lecturas).values(
                    planta_id=lectura.planta_id,
                    origen=lectura.origen,
                    dispositivo_id=lectura.dispositivo_id,
                    humedad=lectura.humedad,
                    luz=lectura.luz,
                    temperatura=lectura.temperatura,
                    estado=lectura.estado,
                    medida_en=lectura.medida_en,
                ))
        except IntegrityError as error:
            if getattr(error.orig.diag, "constraint_name", None) == "uq_lecturas_dispositivo_id_medida_en":
                raise LecturaDuplicada("El dispositivo ya reportó una lectura con esa marca de tiempo.")
            raise

    def ultima(self, planta_id):
        recientes = self.listar(planta_id, 1)
        return recientes[0] if recientes else None

    def listar(self, planta_id, limite):
        consulta = (
            select(lecturas, dispositivos.c.codigo.label("dispositivo_codigo"))
            .outerjoin(dispositivos, dispositivos.c.id == lecturas.c.dispositivo_id)
            .where(lecturas.c.planta_id == planta_id)
            .order_by(lecturas.c.medida_en.desc(), lecturas.c.id.desc())
            .limit(limite)
        )
        with self.engine.connect() as conexion:
            return [
                Lectura(
                    planta_id = f.planta_id,
                    humedad = f.humedad,
                    luz = f.luz,
                    temperatura = f.temperatura,
                    estado = f.estado,
                    medida_en = f.medida_en,
                    origen = f.origen,
                    dispositivo_id = f.dispositivo_id,
                    dispositivo_codigo = f.dispositivo_codigo
                )
                for f in conexion.execute(consulta)
            ]
