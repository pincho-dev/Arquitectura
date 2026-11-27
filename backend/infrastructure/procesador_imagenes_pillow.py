import io
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from domain.fotos import FORMATOS_PERMITIDOS, LADO_MAXIMO_PX, PIXELES_MAXIMOS, ImagenInvalida, ImagenNormalizada
from domain.puertos import ProcesadorImagenes

CALIDAD_WEBP = 85


class ProcesadorImagenesPillow(ProcesadorImagenes):

    def normalizar(self, contenido):
        imagen = self._abrir(contenido)
        # El teléfono guarda la foto "de lado" y anota el giro en el EXIF; como
        # el EXIF se va a borrar, primero se aplica el giro a los píxeles.
        imagen = ImageOps.exif_transpose(imagen)
        imagen.thumbnail((LADO_MAXIMO_PX, LADO_MAXIMO_PX))
        if imagen.mode not in ("RGB", "RGBA"):
            imagen = imagen.convert("RGBA" if "A" in imagen.getbands() or "transparency" in imagen.info else "RGB")

        salida = io.BytesIO()
        # Se guarda una imagen NUEVA solo con los píxeles: sin exif=, sin
        # icc_profile=, sin xmp. Nada del archivo original pasa al guardado.
        imagen.save(salida, "WEBP", quality=CALIDAD_WEBP, method=4)
        return ImagenNormalizada(salida.getvalue(), "image/webp", imagen.width, imagen.height)

    def _abrir(self, contenido):
        try:
            with warnings.catch_warnings():
                # Pillow solo avisa con imágenes enormes; aquí es un error.
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                imagen = Image.open(io.BytesIO(contenido))
                # Se decide por lo que Pillow reconoce en el contenido, nunca por
                # la extensión del archivo ni el Content-Type del navegador.
                if (imagen.format or "").lower() not in FORMATOS_PERMITIDOS:
                    raise ImagenInvalida("Solo se aceptan fotos JPEG, PNG o WebP.")
                if imagen.width * imagen.height > PIXELES_MAXIMOS:
                    raise ImagenInvalida("La foto tiene demasiados píxeles.")
                imagen.load()
                return imagen
        except ImagenInvalida:
            raise
        except (UnidentifiedImageError, Image.DecompressionBombWarning, Image.DecompressionBombError):
            raise ImagenInvalida("El archivo no es una foto válida (JPEG, PNG o WebP).")
        except (OSError, SyntaxError, ValueError):
            raise ImagenInvalida("La foto está dañada o incompleta.")
