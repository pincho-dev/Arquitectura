"""
Lectores RFID de la estación de fábrica.

  LectorRfidSerial    RC522 conectado a un ESP32/Arduino con el sketch
                      firmware/estacion_rfid/, que manda por USB-serial:
                        LISTO RC522 version=0x92   al arrancar (cableado OK)
                        ERROR RC522 ...            si el módulo no responde
                        UID 04A1B2C3               al acercar una tarjeta
                        RETIRADA                   al retirarla
  LectorRfidSimulado  sin hardware, para probar el flujo de punta a punta

Los dos exponen lo mismo: leer_uid() -> 'UID en hexadecimal'.

Por qué el RC522 no va directo al PC: es un módulo SPI, no USB. El ESP32 (o
un Arduino) hace de puente y solo reenvía el UID por el cable USB.
"""
import secrets
import time

ESPERA_ARRANQUE_S = 6   # el ESP32 se reinicia al abrir el puerto serie


class ErrorDeLector(Exception):
    pass


def _detectar_puerto():
    from serial.tools import list_ports
    candidatos = [p.device for p in list_ports.comports()
                  if "ttyUSB" in p.device or "ttyACM" in p.device or p.device.upper().startswith("COM")]
    if not candidatos:
        raise SystemExit(
            "No se encontró el ESP32/Arduino del lector RFID. Conéctalo por USB o pasa --puerto "
            "(ej. /dev/ttyUSB0). Ver la sección 'Lector RC522' de fabrica/README.md.")
    return candidatos[0]


class LectorRfidSerial:
    def __init__(self, puerto=None, baudios=115200):
        try:
            import serial
        except ImportError as error:
            raise SystemExit("Falta pyserial: pip install -r requirements.txt") from error
        self.puerto = puerto or _detectar_puerto()
        try:
            self.serie = serial.Serial(self.puerto, baudios, timeout=0.5)
        except serial.SerialException as error:
            raise SystemExit(
                f"No se pudo abrir {self.puerto}: {error}\n"
                "Si es 'Permission denied': sudo usermod -aG uucp $USER (Arch) o dialout (Ubuntu), "
                "y cierra sesión. Cierra también el Monitor Serie del Arduino IDE.") from error
        self.version = self._esperar_listo()

    def _linea(self):
        return self.serie.readline().decode("ascii", errors="replace").strip()

    def _esperar_listo(self):
        limite = time.monotonic() + ESPERA_ARRANQUE_S
        while time.monotonic() < limite:
            linea = self._linea()
            if linea.startswith("LISTO"):
                return linea.partition("version=")[2] or "?"
            if linea.startswith("ERROR"):
                raise SystemExit(f"El lector respondió: {linea}\nRevisa el cableado (3.3V, NO 5V) en fabrica/README.md.")
        # Algunas placas no se reinician al abrir el puerto: se pide el saludo de nuevo.
        self.serie.write(b"?\n")
        linea = self._linea()
        if linea.startswith("LISTO"):
            return linea.partition("version=")[2] or "?"
        raise SystemExit(f"{self.puerto} no respondió como estación RFID. ¿Subiste firmware/estacion_rfid/ a la placa?")

    def descripcion(self):
        return f"lector RC522 en {self.puerto} (chip {self.version})"

    def leer_uid(self):
        """Bloquea hasta que se acerque una tarjeta. Ctrl+C lanza KeyboardInterrupt."""
        self.serie.reset_input_buffer()   # descarta tarjetas leídas antes de pedirla
        while True:
            linea = self._linea()
            if linea.startswith("UID "):
                return linea[4:].strip().upper()
            if linea.startswith("ERROR"):
                raise ErrorDeLector(linea)

    def esperar_retiro(self):
        while self._linea() != "RETIRADA":
            pass

    def cerrar(self):
        self.serie.close()


class LectorRfidSimulado:
    """Inventa UIDs de 4 bytes como los de las tarjetas MIFARE Classic del kit."""

    def __init__(self):
        self.leidos = []

    def descripcion(self):
        return "lector simulado (sin hardware)"

    def leer_uid(self):
        uid = secrets.token_hex(4).upper()
        self.leidos.append(uid)
        return uid

    def esperar_retiro(self):
        pass

    def cerrar(self):
        pass
