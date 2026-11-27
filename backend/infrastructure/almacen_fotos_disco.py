import os
import re
from pathlib import Path

from domain.puertos import AlmacenFotos

# Las claves las genera el caso de uso (32 hex). Validarlas aquí impide que
# una clave rara arme una ruta fuera de la carpeta (ej. "../../.env").
_CLAVE_VALIDA = re.compile(r"^[0-9a-f]{32}$")


class AlmacenFotosDisco(AlmacenFotos):

    def __init__(self, carpeta):
        self.carpeta = Path(carpeta)
        self.carpeta.mkdir(parents=True, exist_ok=True)

    def guardar(self, clave, contenido):
        ruta = self._ruta(clave)
        temporal = ruta.with_suffix(".tmp")
        temporal.write_bytes(contenido)
        os.replace(temporal, ruta)  # atómico: nunca queda una foto a medio escribir

    def abrir(self, clave):
        try:
            return self._ruta(clave).read_bytes()
        except (FileNotFoundError, ValueError):
            return None

    def eliminar(self, clave):
        try:
            self._ruta(clave).unlink(missing_ok=True)
        except ValueError:
            pass

    def _ruta(self, clave):
        if not _CLAVE_VALIDA.match(clave or ""):
            raise ValueError("Clave de foto inválida.")
        return self.carpeta / f"{clave}.img"
