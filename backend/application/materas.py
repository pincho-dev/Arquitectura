from domain.plantas import ClaveDeReclamoInvalida, DatosDePlantaInvalidos, MateraYaReclamada
from domain.puertos_entrada import FabricarMateraPort, ReclamarMateraPort


class FabricarMatera(FabricarMateraPort):
    """Lo que haría la fábrica: grabar el token en el firmware y la clave de
    reclamo en el sticker NFC de la matera."""

    def __init__(self, repositorio_dispositivos, generador_tokens):
        self.repositorio_dispositivos = repositorio_dispositivos
        self.generador_tokens = generador_tokens

    def ejecutar(self, codigo, especie):
        codigo = codigo.strip().upper()
        if not codigo:
            raise DatosDePlantaInvalidos("El código de la matera no puede estar vacío.", campo="codigo")
        token = self.generador_tokens.generar()
        clave = self.generador_tokens.generar_clave_reclamo()
        dispositivo = self.repositorio_dispositivos.registrar_de_fabrica(codigo, especie.strip().lower(), token, clave)
        return dispositivo, token, clave


class ReclamarMatera(ReclamarMateraPort):

    def __init__(self, repositorio_dispositivos, repositorio_plantas):
        self.repositorio_dispositivos = repositorio_dispositivos
        self.repositorio_plantas = repositorio_plantas

    def ejecutar(self, usuario_id, codigo, clave_reclamo, nombre=None, especie=None):
        codigo = codigo.strip().upper()
        dispositivo = self.repositorio_dispositivos.buscar_para_reclamo(codigo, clave_reclamo.strip())
        if dispositivo is None:
            raise ClaveDeReclamoInvalida("El sticker no corresponde a ninguna matera.")
        if dispositivo.tiene_dueno():
            raise MateraYaReclamada(f"La matera {codigo} ya pertenece a una cuenta.")

        nombre = (nombre or "").strip() or f"Matera {codigo}"
        especie = (especie or "").strip().lower() or dispositivo.especie
        if not especie:
            raise DatosDePlantaInvalidos("Indica la especie de la planta.", campo="especie")

        planta = self.repositorio_plantas.crear(nombre, especie, usuario_id)
        if not self.repositorio_dispositivos.asignar_planta(dispositivo.id, planta.id):
            # Otro usuario la reclamó entre la búsqueda y la asignación:
            # se deshace la planta recién creada.
            self.repositorio_plantas.eliminar(planta.id)
            raise MateraYaReclamada(f"La matera {codigo} ya pertenece a una cuenta.")

        dispositivo.planta_id = planta.id
        return planta, dispositivo
