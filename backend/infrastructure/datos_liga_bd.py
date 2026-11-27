from sqlalchemy import select

from domain.liga import Participante
from domain.plantas import ORIGEN_DISPOSITIVO
from domain.puertos import DatosLiga
from infrastructure.db.tablas import lecturas, plantas, usuario_planta, usuarios


class DatosLigaBd(DatosLiga):

    def __init__(self, engine):
        self.engine = engine

    def participantes(self, usuario_ids=None):
        consulta = (
            select(usuarios.c.id, usuarios.c.nombre, plantas.c.id.label("planta_id"),
                   plantas.c.nombre.label("planta_nombre"))
            .select_from(usuarios)
            .outerjoin(usuario_planta, usuario_planta.c.usuario_id == usuarios.c.id)
            .outerjoin(plantas, plantas.c.id == usuario_planta.c.planta_id)
            .where(usuarios.c.activo)
            .order_by(usuarios.c.id, plantas.c.id)
        )
        if usuario_ids is None:
            consulta = consulta.where(plantas.c.id.is_not(None))
        else:
            consulta = consulta.where(usuarios.c.id.in_(list(usuario_ids)))

        por_usuario = {}
        with self.engine.connect() as conexion:
            for f in conexion.execute(consulta):
                nombre, lista = por_usuario.setdefault(f.id, (f.nombre, []))
                if f.planta_id is not None:
                    lista.append((f.planta_id, f.planta_nombre))
        return [Participante(uid, nombre, tuple(lista)) for uid, (nombre, lista) in por_usuario.items()]

    def estados(self, planta_ids, desde, hasta):
        # Usa el índice (planta_id, medida_en). Trae solo dos columnas: una
        # matera que reporta cada 10 s son unas 260.000 filas al mes.
        consulta = (
            select(lecturas.c.planta_id, lecturas.c.medida_en, lecturas.c.estado)
            .where(
                lecturas.c.planta_id.in_(list(planta_ids)),
                lecturas.c.origen == ORIGEN_DISPOSITIVO,
                lecturas.c.medida_en >= desde,
                lecturas.c.medida_en < hasta,
            )
            .order_by(lecturas.c.planta_id, lecturas.c.medida_en)
        )
        resultado = {}
        with self.engine.connect() as conexion:
            for planta_id, medida_en, estado in conexion.execute(consulta):
                resultado.setdefault(planta_id, []).append((medida_en, estado))
        return resultado
