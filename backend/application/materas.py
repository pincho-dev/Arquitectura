from domain.plantas import (
    ClaveDeReclamoInvalida, DatosDePlantaInvalidos, MateraYaReclamada, TarjetaRfidDesconocida, normalizar_uid_rfid,
)
from domain.puertos_entrada import (
    DescartarMateraPort, FabricarMateraPort, IdentificarMateraPort, ReclamarMateraPort,
)


class FabricarMatera(FabricarMateraPort):
    """Lo que hace la fábrica: el token va al firmware del ESP32, la clave de
    reclamo al QR de la etiqueta y la tarjeta RFID identifica la matera."""

    def __init__(self, repositorio_dispositivos, generador_tokens):
        self.repositorio_dispositivos = repositorio_dispositivos
        self.generador_tokens = generador_tokens

    def ejecutar(self, codigo, especie, rfid_uid=None):
        codigo = codigo.strip().upper()
        if not codigo:
            raise DatosDePlantaInvalidos("El código de la matera no puede estar vacío.", campo="codigo")
        rfid_uid = normalizar_uid_rfid(rfid_uid) if rfid_uid is not None else None
        token = self.generador_tokens.generar()
        clave = self.generador_tokens.generar_clave_reclamo()
        dispositivo = self.repositorio_dispositivos.registrar_de_fabrica(
            codigo, especie.strip().lower(), token, clave, rfid_uid)
        return dispositivo, token, clave


class IdentificarMatera(IdentificarMateraPort):
    """La fábrica acerca la tarjeta al lector y sabe qué matera es (inventario,
    soporte, o para no pegarle la misma tarjeta a dos materas)."""

    def __init__(self, repositorio_dispositivos):
        self.repositorio_dispositivos = repositorio_dispositivos

    def ejecutar(self, rfid_uid):
        dispositivo = self.repositorio_dispositivos.buscar_por_rfid(normalizar_uid_rfid(rfid_uid))
        if dispositivo is None:
            raise TarjetaRfidDesconocida("Esa tarjeta RFID no está asignada a ninguna matera.")
        return dispositivo


class ReclamarMatera(ReclamarMateraPort):

    def __init__(self, repositorio_dispositivos, repositorio_plantas):
        self.repositorio_dispositivos = repositorio_dispositivos
        self.repositorio_plantas = repositorio_plantas

    def ejecutar(self, usuario_id, codigo, clave_reclamo, nombre=None, especie=None):
        codigo = codigo.strip().upper()
        dispositivo = self.repositorio_dispositivos.buscar_para_reclamo(codigo, clave_reclamo.strip())
        if dispositivo is None:
            raise ClaveDeReclamoInvalida("El código y la clave no corresponden a ninguna matera.")
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


class DescartarMatera(DescartarMateraPort):
    """La estación de fábrica no pudo terminar la matera (ej. falló el QR): se
    borra la matera reservada para no dejar una sin etiqueta. Nunca borra una
    ya reclamada."""

    def __init__(self, repositorio_dispositivos):
        self.repositorio_dispositivos = repositorio_dispositivos

    def ejecutar(self, codigo):
        codigo = codigo.strip().upper()
        if not self.repositorio_dispositivos.descartar_sin_reclamar(codigo):
            raise MateraYaReclamada(f"La matera {codigo} no existe o ya pertenece a una cuenta.")
