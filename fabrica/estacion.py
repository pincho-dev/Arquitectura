"""
Estación de fábrica de materas, con lector NFC por USB.

Es la versión física de `flask fabricar-matera`. Por cada matera:
  1. Le pide al backend una matera nueva de la especie del kit
     (POST /api/fabrica/materas). El backend devuelve su código, el token
     del ESP32 y la URL del sticker (reclamar.html?codigo=...&clave=...).
  2. Graba esa URL en un sticker NFC virgen y la relee para verificarla.
     Si la grabación falla, descarta la matera (DELETE) para no dejar una
     sin sticker.
  3. Genera salida/<CODIGO>.h: el config.h del firmware del ESP32
     (token, WiFi y servidor), listo para copiar a firmware/matera_esp32/.
  4. Guarda materas_fabricadas/<CODIGO>.json, igual que el comando de consola,
     para poder probar esa matera con simulador_esp32.py.

El sticker solo lleva la URL con la clave de reclamo. El token del ESP32
nunca va en el sticker: cualquiera que lo toque podría leerlo.

Uso:
  python estacion.py --especie potos               # lector USB (ACR122U o compatible)
  python estacion.py --especie potos --simular     # sin lector, para probar el flujo
  python estacion.py --especie potos --una         # fabrica una sola y termina
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
from lector_nfc import ErrorDeGrabacion, LectorNfcSimulado, LectorNfcUsb

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


def advertencias(config, url_sticker):
    avisos = []
    if config["host"] in ("localhost", "127.0.0.1", ""):
        avisos.append(f"El ESP32 intentará conectarse a '{config['host']}', que para él es él mismo. "
                      "Pon ESP_SERVIDOR=<IP de tu PC>:5000 en fabrica/.env.")
    if not config["ssid"]:
        avisos.append("Falta ESP_WIFI_SSID en fabrica/.env: el ESP32 no sabrá a qué WiFi conectarse.")
    host_sticker = urlparse(url_sticker).hostname
    if host_sticker in ("localhost", "127.0.0.1"):
        avisos.append(f"El sticker apunta a {host_sticker}: el teléfono no lo podrá abrir. "
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
            escritor.writerow(["fecha", "codigo", "especie", "nfc_uid"])
        escritor.writerow([datetime.now().isoformat(timespec="seconds"), matera["codigo"], matera["especie"], uid])


def fabricar_una(api, lector, especie, carpeta_salida, config_esp, codigo=None,
                 carpeta_materas=CARPETA_MATERAS, avisar=print):
    matera = api.fabricar(especie, codigo)
    avisar(f"  → Matera {matera['codigo']} ({matera['especie']}) registrada en el backend")
    for aviso in advertencias(config_esp, matera["url_sticker_nfc"]):
        avisar(f"  ! {aviso}")
    avisar("  → Acerca un sticker NFC virgen al lector…")

    try:
        uid = lector.grabar_url(matera["url_sticker_nfc"])
    except (ErrorDeGrabacion, KeyboardInterrupt):
        # El sticker no quedó grabado: nadie podría reclamar esta matera.
        try:
            api.descartar(matera["codigo"])
            avisar(f"  ↺ Matera {matera['codigo']} descartada.")
        except ErrorApi as error:
            avisar(f"  ! No se pudo descartar {matera['codigo']}: {error}")
        raise

    avisar(f"  → Sticker {uid} grabado y verificado")
    archivo_firmware = escribir_config_firmware(carpeta_salida, matera, config_esp)
    escribir_json_simulador(carpeta_materas, matera)
    registrar_en_bitacora(carpeta_salida, matera, uid)
    return matera, uid, archivo_firmware


def main():
    parser = argparse.ArgumentParser(description="Estación de fábrica de materas con lector NFC")
    parser.add_argument("--especie", required=True, help="especie del kit (ej. potos)")
    parser.add_argument("--codigo", help="código de la matera (solo con --una); si no, lo genera el backend")
    parser.add_argument("--simular", action="store_true", help="sin lector NFC (prueba del flujo)")
    parser.add_argument("--dispositivo", default="usb", help="lector para nfcpy (por defecto 'usb')")
    parser.add_argument("--una", action="store_true", help="fabricar una sola matera y salir")
    parser.add_argument("--forzar", action="store_true", help="sobrescribir stickers que ya tengan datos")
    parser.add_argument("--bloquear", action="store_true",
                        help="dejar el sticker de solo lectura (IRREVERSIBLE; solo para producción)")
    parser.add_argument("--salida", default=str(CARPETA / "salida"))
    args = parser.parse_args()
    if args.codigo and not args.una:
        parser.error("--codigo solo tiene sentido con --una")

    url_api = os.environ.get("FABRICA_API", "http://localhost:5000")
    clave = os.environ.get("FABRICA_CLAVE")
    if not clave:
        sys.exit("Falta FABRICA_CLAVE en fabrica/.env (la misma del .env del backend).")
    api = ClienteFabrica(url_api, clave)

    config_esp = configuracion_esp(url_api)
    lector = LectorNfcSimulado() if args.simular else LectorNfcUsb(args.dispositivo, args.forzar, args.bloquear)
    print(f"Estación de fábrica · backend {url_api} · {lector.descripcion()}")
    print(f"Los ESP32 se conectarán a ws://{config_esp['host']}:{config_esp['puerto']}/ws/dispositivos "
          f"por el WiFi '{config_esp['ssid']}'")
    if args.bloquear:
        print("ATENCIÓN: --bloquear deja cada sticker de solo lectura para siempre.")

    fabricadas = 0
    try:
        while True:
            if not args.una:
                input(f"\nEnter para fabricar otra matera de {args.especie} (Ctrl+C para salir)… ")
            try:
                matera, _, archivo = fabricar_una(api, lector, args.especie, Path(args.salida), config_esp, args.codigo)
            except (ErrorApi, ErrorDeGrabacion) as error:
                print(f"  ✗ {error}")
                if args.una:
                    sys.exit(1)
                continue

            fabricadas += 1
            print(f"  ✓ {matera['codigo']} lista. Imprime este código en la etiqueta de la matera.")
            print(f"    Firmware del ESP32: copia {archivo} como firmware/matera_esp32/config.h")
            if args.una:
                break
            print("  → Retira el sticker del lector…")
            lector.esperar_retiro()
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        lector.cerrar()
        print(f"Materas fabricadas en esta sesión: {fabricadas}")


if __name__ == "__main__":
    main()
