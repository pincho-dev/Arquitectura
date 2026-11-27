"""
Galería de fotos de plantas (gamificación: presumir la planta).

Reglas:
- Solo un dueño de la planta puede subirle fotos.
- La foto queda ligada a la planta con una copia de su ÚLTIMA LECTURA al
  momento de subirla: lo que se presume son datos reales, no un texto.
- La galería la ven todos los usuarios registrados.
- Borra la foto quien la subió o cualquier dueño de la planta.
- Toda imagen se valida por su CONTENIDO (no por la extensión ni por el tipo
  que declare el navegador) y se vuelve a codificar: así se pierden el EXIF
  (la ubicación GPS de la casa, el modelo del teléfono) y cualquier cosa que
  venga escondida en el archivo.
"""

FORMATOS_PERMITIDOS = ("jpeg", "png", "webp")
TAMANO_MAXIMO_BYTES = 10 * 1024 * 1024
LADO_MAXIMO_PX = 1600
PIXELES_MAXIMOS = 40_000_000  # una foto de 40 MP; más que eso es sospechoso (bomba de descompresión)
DESCRIPCION_MAXIMA = 280


class ImagenInvalida(Exception):
    pass


class FotoNoEncontrada(Exception):
    pass


class DatosDeFotoInvalidos(Exception):
    def __init__(self, mensaje, campo=None):
        super().__init__(mensaje)
        self.campo = campo


class ImagenNormalizada:
    """La imagen ya limpia y lista para guardar."""

    def __init__(self, contenido, tipo, ancho, alto):
        self.contenido = contenido
        self.tipo = tipo  # tipo MIME, ej. "image/webp"
        self.ancho = ancho
        self.alto = alto


class Foto:
    def __init__(self, id, planta_id, planta_nombre, especie, autor_id, autor_nombre, clave_archivo,
                 tipo, ancho, alto, descripcion=None, lectura=None, creada_en=None, duenos_planta=()):
        self.id = id
        self.planta_id = planta_id
        self.planta_nombre = planta_nombre
        self.especie = especie
        self.autor_id = autor_id
        self.autor_nombre = autor_nombre
        self.clave_archivo = clave_archivo
        self.tipo = tipo
        self.ancho = ancho
        self.alto = alto
        self.descripcion = descripcion
        # Copia de la última lectura de la planta al subir la foto (o None).
        self.lectura = lectura
        self.creada_en = creada_en
        self.duenos_planta = frozenset(duenos_planta)

    def puede_borrar(self, usuario_id):
        return usuario_id == self.autor_id or usuario_id in self.duenos_planta


def validar_descripcion(texto):
    if texto is None:
        return None
    texto = texto.strip()
    if len(texto) > DESCRIPCION_MAXIMA:
        raise DatosDeFotoInvalidos(
            f"La descripción es muy larga (máx. {DESCRIPCION_MAXIMA} caracteres).", campo="descripcion")
    return texto or None


def validar_tamano(contenido):
    if not contenido:
        raise ImagenInvalida("El archivo está vacío.")
    if len(contenido) > TAMANO_MAXIMO_BYTES:
        raise ImagenInvalida(f"La foto pesa más de {TAMANO_MAXIMO_BYTES // (1024 * 1024)} MB.")
