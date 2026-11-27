from sqlalchemy import delete, insert, select

from domain.fotos import Foto
from domain.puertos import RepositorioFotos
from infrastructure.db.tablas import especies, fotos, plantas, usuario_planta, usuarios


class RepositorioFotosBd(RepositorioFotos):

    def __init__(self, engine):
        self.engine = engine

    def crear(self, planta_id, autor_id, clave_archivo, tipo, ancho, alto, descripcion, lectura):
        valores = dict(planta_id=planta_id, autor_id=autor_id, clave_archivo=clave_archivo, tipo=tipo,
                       ancho=ancho, alto=alto, descripcion=descripcion)
        if lectura is not None:
            valores.update(estado=lectura.estado, humedad=lectura.humedad, luz=lectura.luz,
                           temperatura=lectura.temperatura, medida_en=lectura.medida_en)
        with self.engine.begin() as conexion:
            foto_id = conexion.execute(insert(fotos).values(**valores).returning(fotos.c.id)).scalar_one()
        return self.buscar(foto_id)

    def buscar(self, foto_id):
        filas = self._consultar(fotos.c.id == foto_id, limite=1)
        return filas[0] if filas else None

    def listar(self, limite, antes_de=None, planta_id=None):
        condiciones = []
        if antes_de is not None:
            condiciones.append(fotos.c.id < antes_de)
        if planta_id is not None:
            condiciones.append(fotos.c.planta_id == planta_id)
        return self._consultar(*condiciones, limite=limite)

    def eliminar(self, foto_id):
        with self.engine.begin() as conexion:
            conexion.execute(delete(fotos).where(fotos.c.id == foto_id))

    def _consultar(self, *condiciones, limite):
        consulta = (
            select(fotos, plantas.c.nombre.label("planta_nombre"), especies.c.nombre.label("especie"),
                   usuarios.c.nombre.label("autor_nombre"))
            .join(plantas, plantas.c.id == fotos.c.planta_id)
            .join(especies, especies.c.id == plantas.c.especie_id)
            .join(usuarios, usuarios.c.id == fotos.c.autor_id)
            .where(*condiciones)
            # El id crece con cada foto: sirve de orden y de cursor para "cargar más".
            .order_by(fotos.c.id.desc())
            .limit(limite)
        )
        with self.engine.connect() as conexion:
            filas = conexion.execute(consulta).all()
            planta_ids = {f.planta_id for f in filas}
            duenos = {}
            if planta_ids:
                for planta_id, usuario_id in conexion.execute(
                        select(usuario_planta.c.planta_id, usuario_planta.c.usuario_id)
                        .where(usuario_planta.c.planta_id.in_(planta_ids))):
                    duenos.setdefault(planta_id, set()).add(usuario_id)
        return [self._a_foto(f, duenos.get(f.planta_id, ())) for f in filas]

    def _a_foto(self, f, duenos):
        lectura = None
        if f.estado is not None:
            lectura = {"estado": f.estado, "humedad": f.humedad, "luz": f.luz,
                       "temperatura": f.temperatura, "medida_en": f.medida_en}
        return Foto(
            id=f.id, planta_id=f.planta_id, planta_nombre=f.planta_nombre, especie=f.especie,
            autor_id=f.autor_id, autor_nombre=f.autor_nombre, clave_archivo=f.clave_archivo,
            tipo=f.tipo, ancho=f.ancho, alto=f.alto, descripcion=f.descripcion, lectura=lectura,
            creada_en=f.creado_en, duenos_planta=duenos,
        )
