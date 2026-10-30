from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError

from domain.puertos import RepositorioUsuarios
from domain.usuarios import EmailYaRegistrado, Usuario
from infrastructure.db.tablas import roles, usuario_roles, usuarios

ROL_POR_DEFECTO = "usuario"


class RepositorioUsuariosBd(RepositorioUsuarios):

    def __init__(self, engine):
        self.engine = engine

    def buscar_por_email(self, email):
        with self.engine.connect() as conexion:
            fila = conexion.execute(
                select(usuarios).where(usuarios.c.email == email)
            ).mappings().first()
        return self._a_usuario(fila) if fila else None

    def crear(self, nombre, email, password_hash):
        try:
            with self.engine.begin() as conexion:
                fila = conexion.execute(
                    insert(usuarios)
                    .values(nombre=nombre, email=email, password_hash=password_hash)
                    .returning(usuarios)
                ).mappings().one()
                conexion.execute(
                    insert(usuario_roles).from_select(
                        ["usuario_id", "rol_id"],
                        select(fila["id"], roles.c.id).where(roles.c.nombre == ROL_POR_DEFECTO),
                    )
                )
        except IntegrityError as error:
            # La restricción única de la BD es la garantía real (dos registros
            # simultáneos con el mismo correo), no una consulta previa.
            if getattr(error.orig.diag, "constraint_name", None) == "uq_usuarios_email":
                raise EmailYaRegistrado(f"El correo '{email}' ya está registrado.")
            raise
        return self._a_usuario(fila)

    def _a_usuario(self, fila):
        return Usuario(
            id = fila["id"],
            nombre = fila["nombre"],
            email = fila["email"],
            password_hash = fila["password_hash"],
            activo = fila["activo"]
        )
