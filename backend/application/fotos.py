import secrets

from domain.fotos import FotoNoEncontrada, validar_descripcion, validar_tamano
from domain.plantas import AccesoDenegado, PlantaNoEncontrada
from domain.puertos_entrada import EliminarFotoPort, ListarFotosPort, SubirFotoPort, VerFotoPort

LIMITE_MAXIMO = 50


class SubirFoto(SubirFotoPort):

    def __init__(self, repositorio_plantas, historial_lecturas, repositorio_fotos, almacen_fotos, procesador_imagenes):
        self.repositorio_plantas = repositorio_plantas
        self.historial_lecturas = historial_lecturas
        self.repositorio_fotos = repositorio_fotos
        self.almacen_fotos = almacen_fotos
        self.procesador_imagenes = procesador_imagenes

    def ejecutar(self, usuario_id, planta_id, contenido, descripcion=None):
        planta = self.repositorio_plantas.buscar(planta_id)
        if planta is None:
            raise PlantaNoEncontrada(f"La planta {planta_id} no existe.")
        planta.verificar_acceso(usuario_id)
        descripcion = validar_descripcion(descripcion)
        validar_tamano(contenido)

        imagen = self.procesador_imagenes.normalizar(contenido)
        # Nombre aleatorio: no revela nada (ni el nombre original del archivo
        # ni el orden de subida) y no se puede adivinar.
        clave = secrets.token_hex(16)
        self.almacen_fotos.guardar(clave, imagen.contenido)
        try:
            return self.repositorio_fotos.crear(
                planta_id=planta.id,
                autor_id=usuario_id,
                clave_archivo=clave,
                tipo=imagen.tipo,
                ancho=imagen.ancho,
                alto=imagen.alto,
                descripcion=descripcion,
                lectura=self.historial_lecturas.ultima(planta.id),
            )
        except Exception:
            # Sin fila en la BD el archivo quedaría huérfano para siempre.
            self.almacen_fotos.eliminar(clave)
            raise


class ListarFotos(ListarFotosPort):

    def __init__(self, repositorio_fotos):
        self.repositorio_fotos = repositorio_fotos

    def ejecutar(self, limite, antes_de=None, planta_id=None):
        return self.repositorio_fotos.listar(min(max(limite, 1), LIMITE_MAXIMO), antes_de, planta_id)


class VerFoto(VerFotoPort):

    def __init__(self, repositorio_fotos, almacen_fotos):
        self.repositorio_fotos = repositorio_fotos
        self.almacen_fotos = almacen_fotos

    def ejecutar(self, foto_id):
        foto = self.repositorio_fotos.buscar(foto_id)
        contenido = self.almacen_fotos.abrir(foto.clave_archivo) if foto else None
        if contenido is None:
            raise FotoNoEncontrada("La foto no existe.")
        return foto, contenido


class EliminarFoto(EliminarFotoPort):

    def __init__(self, repositorio_fotos, almacen_fotos):
        self.repositorio_fotos = repositorio_fotos
        self.almacen_fotos = almacen_fotos

    def ejecutar(self, usuario_id, foto_id):
        foto = self.repositorio_fotos.buscar(foto_id)
        if foto is None:
            raise FotoNoEncontrada("La foto no existe.")
        if not foto.puede_borrar(usuario_id):
            raise AccesoDenegado("Solo quien subió la foto o un dueño de la planta puede borrarla.")
        # Primero la fila: si falla el borrado del archivo, la foto ya no se ve.
        self.repositorio_fotos.eliminar(foto.id)
        self.almacen_fotos.eliminar(foto.clave_archivo)
