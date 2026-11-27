from sqlalchemy import and_, delete, insert, or_, select, update
from sqlalchemy.exc import IntegrityError

from domain.amistades import Amistad, SolicitudYaExiste
from domain.puertos import RepositorioAmistades
from infrastructure.db.tablas import amistades, usuarios

_solicitante = usuarios.alias("solicitante")
_destinatario = usuarios.alias("destinatario")


class RepositorioAmistadesBd(RepositorioAmistades):

    def __init__(self, engine):
        self.engine = engine

    def buscar(self, amistad_id):
        filas = self._consultar(amistades.c.id == amistad_id)
        return filas[0] if filas else None

    def buscar_entre(self, usuario_a, usuario_b):
        filas = self._consultar(or_(
            and_(amistades.c.solicitante_id == usuario_a, amistades.c.destinatario_id == usuario_b),
            and_(amistades.c.solicitante_id == usuario_b, amistades.c.destinatario_id == usuario_a),
        ))
        return filas[0] if filas else None

    def crear(self, solicitante_id, destinatario_id):
        try:
            with self.engine.begin() as conexion:
                amistad_id = conexion.execute(
                    insert(amistades)
                    .values(solicitante_id=solicitante_id, destinatario_id=destinatario_id)
                    .returning(amistades.c.id)
                ).scalar_one()
        except IntegrityError as error:
            # Dos solicitudes cruzadas al mismo tiempo: la garantía real es el índice único.
            if getattr(error.orig.diag, "constraint_name", None) == "uq_amistades_par":
                raise SolicitudYaExiste("Ya hay una solicitud de amistad entre ustedes.")
            raise
        return self.buscar(amistad_id)

    def aceptar(self, amistad_id, cuando):
        with self.engine.begin() as conexion:
            conexion.execute(
                update(amistades)
                .where(amistades.c.id == amistad_id, amistades.c.aceptada_en.is_(None))
                .values(aceptada_en=cuando)
            )

    def eliminar(self, amistad_id):
        with self.engine.begin() as conexion:
            conexion.execute(delete(amistades).where(amistades.c.id == amistad_id))

    def listar_de_usuario(self, usuario_id):
        return self._consultar(or_(
            amistades.c.solicitante_id == usuario_id, amistades.c.destinatario_id == usuario_id,
        ))

    def ids_amigos(self, usuario_id):
        return {
            a.otro(usuario_id)[0] for a in self.listar_de_usuario(usuario_id) if a.aceptada
        }

    def _consultar(self, condicion):
        consulta = (
            select(amistades, _solicitante.c.nombre.label("solicitante_nombre"),
                   _destinatario.c.nombre.label("destinatario_nombre"))
            .join(_solicitante, _solicitante.c.id == amistades.c.solicitante_id)
            .join(_destinatario, _destinatario.c.id == amistades.c.destinatario_id)
            .where(condicion)
            .order_by(amistades.c.creado_en.desc(), amistades.c.id.desc())
        )
        with self.engine.connect() as conexion:
            return [
                Amistad(
                    id=f.id,
                    solicitante_id=f.solicitante_id,
                    solicitante_nombre=f.solicitante_nombre,
                    destinatario_id=f.destinatario_id,
                    destinatario_nombre=f.destinatario_nombre,
                    aceptada_en=f.aceptada_en,
                    creada_en=f.creado_en,
                )
                for f in conexion.execute(consulta)
            ]
