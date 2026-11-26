"""
Estación de fábrica de materas: QR de reclamo y, opcionalmente, tarjeta RFID.

Es la versión física de `flask fabricar-matera`. Por cada matera:
  1. (Solo con --rfid) Se acerca al lector la tarjeta RFID que va pegada a la
     matera. El RC522 está conectado a un ESP32/Arduino (firmware/estacion_rfid/)
     que manda el UID por USB-serial.
  2. Se le pide al backend una matera nueva de la especie del kit (con el UID,
     si hay) (POST /api/fabrica/materas). El backend devuelve su código, el token del
     ESP32 y la URL de reclamo (reclamar.html?codigo=...&clave=...). Si la
     tarjeta ya está en otra matera, el backend responde 409 y no se crea nada.
  3. Genera salida/<CODIGO>_etiqueta.png: el QR de reclamo + código + clave,
     para imprimir y pegar en la matera. Si falla, descarta la matera (DELETE).
  4. Genera salida/<CODIGO>.h: el config.h del firmware del ESP32 (token, WiFi
     y servidor), listo para copiar a firmware/matera_esp32/.
  5. Guarda materas_fabricadas/<CODIGO>.json, igual que el comando de consola,
     para poder probar esa matera con simulador_esp32.py.

Lo que vincula la ESP con la planta del usuario es el CÓDIGO de la matera: el
token (firmware) y la clave (QR) son de ese código. La tarjeta RFID no hace
falta para eso; solo identifica la matera dentro de la fábrica (inventario,
soporte). El celular no puede leer estas tarjetas (el iPhone no lee MIFARE
Classic), por eso el usuario reclama con el QR. El token del ESP32 no va ni en
la tarjeta ni en el QR.

Uso:
  python estacion.py --especie potos                        # solo QR (no necesita lector)
  python estacion.py --especie potos --una                  # una sola y termina
  python estacion.py --especie potos --rfid                 # + tarjeta RFID con el RC522 por USB
  python estacion.py --especie potos --rfid --simular       # + tarjeta RFID simulada
  python estacion.py --identificar                          # acercar tarjetas y ver de qué matera son
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from cliente_api import ClienteFabrica, ErrorApi
from etiqueta import generar_etiqueta, qr_en_terminal
from lector_rfid import ErrorDeLector, LectorRfidSerial, LectorRfidSimulado

CARPETA = Path(__file__).resolve().parent
CARPETA_MATERAS = CARPETA.parent / "materas_fabricadas"
load_dotenv(CARPETA / ".env")


def _cadena_c(valor):
    return '"' + valor.replace("\\", "\\\\").replace('"', '\\"') + '"'


def configuracion_esp(url_api):
    """A dónde se conecta el ESP32 y con qué WiFi. Sale de fabrica/.env."""
    servidor = os.environ.get("ESP_SERVIDOR") or urlparse(url_api).netloc
    host, _, puerto = servidor.partition(":")
    return {
        "host": host,
        "puerto": int(puerto or 5000),
        "ssid": os.environ.get("ESP_WIFI_SSID", ""),
        "clave": os.environ.get("ESP_WIFI_CLAVE", ""),
    }


class ErrorDeEtiqueta(Exception):
    pass


def advertencias(config, url_reclamo):
    avisos = []
    if config["host"] in ("localhost", "127.0.0.1", ""):
        avisos.append(f"El ESP32 intentará conectarse a '{config['host']}', que para él es él mismo. "
                      "Pon ESP_SERVIDOR=<IP de tu PC>:5000 en fabrica/.env.")
    if not config["ssid"]:
        avisos.append("Falta ESP_WIFI_SSID en fabrica/.env: el ESP32 no sabrá a qué WiFi conectarse.")
    host_qr = urlparse(url_reclamo).hostname
    if host_qr in ("localhost", "127.0.0.1"):
        avisos.append(f"El QR apunta a {host_qr}: el teléfono no lo podrá abrir. "
                      "Pon FRONT_URL=http://<IP de tu PC>:5500 en backend/.env y reinicia el backend.")
    return avisos


def escribir_config_firmware(carpeta_salida, matera, config):
    carpeta_salida.mkdir(parents=True, exist_ok=True)
    archivo = carpeta_salida / f"{matera['codigo']}.h"
    archivo.write_text(
        f"// Matera {matera['codigo']} ({matera['especie']}) - generado por la estación de fábrica el "
        f"{datetime.now():%Y-%m-%d %H:%M}.\n"
        f"// Copiar como firmware/matera_esp32/config.h antes de compilar.\n"
        f"// Contiene el token del dispositivo y la clave del WiFi: NO subir a git.\n"
        f"#pragma once\n\n"
        f"#define WIFI_SSID        {_cadena_c(config['ssid'])}\n"
        f"#define WIFI_CLAVE       {_cadena_c(config['clave'])}\n\n"
        f"#define SERVIDOR_HOST    {_cadena_c(config['host'])}\n"
        f"#define SERVIDOR_PUERTO  {config['puerto']}\n\n"
        f"#define CODIGO_MATERA    {_cadena_c(matera['codigo'])}\n"
        f"#define TOKEN_MATERA     {_cadena_c(matera['token_firmware'])}\n",
        encoding="utf-8",
    )
    return archivo


def escribir_json_simulador(carpeta, matera):
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / f"{matera['codigo']}.json"
    archivo.write_text(json.dumps(matera, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return archivo


def registrar_en_bitacora(carpeta_salida, matera, uid):
    archivo = carpeta_salida / "registro_fabricacion.csv"
    nuevo = not archivo.exists()
    with archivo.open("a", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        if nuevo:
            escritor.writerow(["fecha", "codigo", "especie", "rfid_uid"])
        escritor.writerow([datetime.now().isoformat(timespec="seconds"), matera["codigo"], matera["especie"], uid])


def fabricar_una(api, lector, especie, carpeta_salida, config_esp, codigo=None,
                 carpeta_materas=CARPETA_MATERAS, avisar=print):
    uid = None
    if lector is not None:    # el lector RFID es opcional
        avisar("  → Acerca al lector la tarjeta RFID de la matera…")
        uid = lector.leer_uid()
        avisar(f"  → Tarjeta {uid}")

    # Si la tarjeta ya está en otra matera, el backend responde 409 y aquí no
    # queda nada que deshacer.
    matera = api.fabricar(especie, codigo, rfid_uid=uid)
    avisar(f"  → Matera {matera['codigo']} ({matera['especie']}) registrada en el backend")
    for aviso in advertencias(config_esp, matera["url_reclamo"]):
        avisar(f"  ! {aviso}")

    try:
        etiqueta = generar_etiqueta(carpeta_salida, matera)
    except Exception as error:
        # Sin etiqueta nadie podría reclamar esta matera: se descarta.
        try:
            api.descartar(matera["codigo"])
            avisar(f"  ↺ Matera {matera['codigo']} descartada.")
        except ErrorApi as error_api:
            avisar(f"  ! No se pudo descartar {matera['codigo']}: {error_api}")
        raise ErrorDeEtiqueta(f"No se pudo generar la etiqueta con el QR: {error}") from error

    archivo_firmware = escribir_config_firmware(carpeta_salida, matera, config_esp)
    escribir_json_simulador(carpeta_materas, matera)
    registrar_en_bitacora(carpeta_salida, matera, uid)
    return matera, etiqueta, archivo_firmware


def identificar(api, lector):
    """Modo --identificar: acercar tarjetas y ver a qué matera pertenecen."""
    print("Acerca una tarjeta (Ctrl+C para salir)…")
    while True:
        uid = lector.leer_uid()
        try:
            m = api.identificar(uid)
            estado = "ya tiene dueño" if m["reclamada"] else "sin reclamar"
            print(f"  {uid} → {m['codigo']} ({m['especie']}), {estado}")
        except ErrorApi as error:
            print(f"  {uid} → {error}")
        lector.esperar_retiro()


def main():
    parser = argparse.ArgumentParser(description="Estación de fábrica de materas (QR + tarjeta RFID opcional)")
    parser.add_argument("--especie", help="especie del kit (ej. potos)")
    parser.add_argument("--codigo", help="código de la matera (solo con --una); si no, lo genera el backend")
    parser.add_argument("--rfid", action="store_true", help="pegarle a cada matera una tarjeta RFID (lector RC522)")
    parser.add_argument("--simular", action="store_true", help="con --rfid o --identificar: lector RFID simulado")
    parser.add_argument("--puerto", help="puerto serie del ESP32/Arduino (por defecto se detecta, ej. /dev/ttyUSB0)")
    parser.add_argument("--una", action="store_true", help="fabricar una sola matera y salir")
    parser.add_argument("--identificar", action="store_true", help="solo leer tarjetas y decir de qué matera son")
    parser.add_argument("--salida", default=str(CARPETA / "salida"))
    args = parser.parse_args()
    if args.codigo and not args.una:
        parser.error("--codigo solo tiene sentido con --una")
    if not args.especie and not args.identificar:
        parser.error("falta --especie (o usa --identificar)")

    url_api = os.environ.get("FABRICA_API", "http://localhost:5000")
    clave = os.environ.get("FABRICA_CLAVE")
    if not clave:
        sys.exit("Falta FABRICA_CLAVE en fabrica/.env (la misma del .env del backend).")
    api = ClienteFabrica(url_api, clave)

    lector = None
    if args.rfid or args.identificar:
        lector = LectorRfidSimulado() if args.simular else LectorRfidSerial(args.puerto)
    print(f"Estación de fábrica · backend {url_api} · "
          f"{lector.descripcion() if lector else 'solo QR (sin lector RFID)'}")
    if args.identificar:
        try:
            identificar(api, lector)
        except KeyboardInterrupt:
            print()
        finally:
            lector.cerrar()
        return

    config_esp = configuracion_esp(url_api)
    print(f"Los ESP32 se conectarán a ws://{config_esp['host']}:{config_esp['puerto']}/ws/dispositivos "
          f"por el WiFi '{config_esp['ssid']}'")

    fabricadas = 0
    try:
        while True:
            if not args.una:
                input(f"\nEnter para fabricar otra matera de {args.especie} (Ctrl+C para salir)… ")
            try:
                matera, etiqueta, archivo = fabricar_una(api, lector, args.especie, Path(args.salida),
                                                         config_esp, args.codigo)
            except (ErrorApi, ErrorDeEtiqueta, ErrorDeLector) as error:
                print(f"  ✗ {error}")
                if args.una:
                    sys.exit(1)
                if lector is not None:
                    lector.esperar_retiro()
                continue

            fabricadas += 1
            print(qr_en_terminal(matera["url_reclamo"]))
            print(f"  ✓ {matera['codigo']} lista.")
            print(f"    Etiqueta para imprimir y pegar: {etiqueta}")
            print(f"    URL del QR: {matera['url_reclamo']}")
            print(f"    Firmware del ESP32: copia {archivo} como firmware/matera_esp32/config.h")
            if args.una:
                break
            if lector is not None:
                print("  → Retira la tarjeta del lector…")
                lector.esperar_retiro()
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        if lector is not None:
            lector.cerrar()
        print(f"Materas fabricadas en esta sesión: {fabricadas}")


if __name__ == "__main__":
    main()
