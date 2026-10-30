from domain.plantas import DatosDePlantaInvalidos
from domain.puertos_entrada import CrearPlantaPort


class CrearPlanta(CrearPlantaPort):

    def __init__(self, repositorio_plantas):
        self.repositorio_plantas = repositorio_plantas

    def ejecutar(self, usuario_id, nombre, especie):
        nombre = nombre.strip()
        if not nombre:
            raise DatosDePlantaInvalidos("El nombre de la planta no puede estar vacío.", campo="nombre")
        return self.repositorio_plantas.crear(nombre, especie.strip().lower(), usuario_id)
