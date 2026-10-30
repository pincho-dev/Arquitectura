from domain.plantas import DatosDePlantaInvalidos, PlantaNoEncontrada
from domain.puertos_entrada import VincularDispositivoPort


class VincularDispositivo(VincularDispositivoPort):

    def __init__(self, repositorio_plantas, repositorio_dispositivos, generador_tokens):
        self.repositorio_plantas = repositorio_plantas
        self.repositorio_dispositivos = repositorio_dispositivos
        self.generador_tokens = generador_tokens

    def ejecutar(self, usuario_id, planta_id, codigo):
        codigo = codigo.strip().upper()
        if not codigo:
            raise DatosDePlantaInvalidos("El código del dispositivo no puede estar vacío.", campo="codigo")

        planta = self.repositorio_plantas.buscar(planta_id)
        if planta is None:
            raise PlantaNoEncontrada(f"La planta {planta_id} no existe.")
        planta.verificar_acceso(usuario_id)

        token = self.generador_tokens.generar()
        dispositivo = self.repositorio_dispositivos.registrar(codigo, planta.id, token)
        return dispositivo, token
