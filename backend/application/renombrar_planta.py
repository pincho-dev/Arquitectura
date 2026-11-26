from domain.plantas import DatosDePlantaInvalidos, PlantaNoEncontrada
from domain.puertos_entrada import RenombrarPlantaPort


class RenombrarPlanta(RenombrarPlantaPort):

    def __init__(self, repositorio_plantas):
        self.repositorio_plantas = repositorio_plantas

    def ejecutar(self, usuario_id, planta_id, nombre):
        planta = self.repositorio_plantas.buscar(planta_id)
        if planta is None:
            raise PlantaNoEncontrada("La planta no existe.")
        planta.verificar_acceso(usuario_id)
        nombre = nombre.strip()
        if not nombre:
            raise DatosDePlantaInvalidos("El nombre de la planta no puede estar vacio.", campo="nombre")
        if len(nombre) > 100:
            raise DatosDePlantaInvalidos("El nombre es muy largo (max. 100).", campo="nombre")
        self.repositorio_plantas.renombrar(planta_id, nombre)
        planta.nombre = nombre
        return planta

