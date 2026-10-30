#!/usr/bin/env python3
"""
Simulador del ESP32 de la matera (R3).

Envía lecturas periódicas a POST /api/dispositivos/<codigo>/lecturas con el
token del dispositivo. Además de lecturas realistas, mete a propósito valores
fuera de rango y datos inválidos para probar la robustez de la API.

Uso con una matera de la fábrica simulada (flujo NFC):
    python simulador_esp32.py --matera materas_fabricadas/MAT-1A2B.json --tocar-nfc

    --matera carga el código, el token y la especie que "trae de fábrica".
    --tocar-nfc abre en el navegador la URL del sticker, como si el teléfono
    lo hubiera leído. Hasta que alguien reclame la matera, el backend
    rechaza sus lecturas (409 MATERA_SIN_DUENO) y el simulador sigue
    intentando: así se ve que cada matera necesita un dueño.

Uso con un dispositivo vinculado a mano:
    python simulador_esp32.py --codigo ESP32-01 --token dev_xxx --intervalo 2 --perfil helecho

El token también puede ir en la variable de entorno MATERA_TOKEN_DISPOSITIVO.
Solo usa la librería estándar de Python: no requiere instalar nada.
"""
import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime, timedelta, timezone

# Condiciones típicas por especie (centro de los rangos del Anexo B).
PERFILES = {
    "sansevieria": {"humedad": 32, "luz": 800, "temperatura": 22},
    "potos": {"humedad": 55, "luz": 700, "temperatura": 24},
    "suculenta": {"humedad": 20, "luz": 1600, "temperatura": 24},
    "helecho": {"humedad": 72, "luz": 450, "temperatura": 21},
    "lavanda": {"humedad": 38, "luz": 2000, "temperatura": 22},
}


class SensorSimulado:
    """Caminata aleatoria alrededor del perfil: la tierra se seca de a poco y
    se riega cuando baja demasiado; luz y temperatura oscilan."""

    def __init__(self, perfil, generador):
        self.base = perfil
        self.valores = dict(perfil)
        self.rnd = generador

    def siguiente(self):
        self.valores["humedad"] -= self.rnd.uniform(0.2, 1.2)
        if self.valores["humedad"] < self.base["humedad"] * 0.7:
            self.valores["humedad"] = self.base["humedad"] * 1.1  # riego
        self.valores["luz"] = max(0, self.valores["luz"] + self.rnd.uniform(-60, 60))
        self.valores["temperatura"] += self.rnd.uniform(-0.4, 0.4)
        return {k: round(v, 1) for k, v in self.valores.items()}

    def fuera_de_rango(self):
        # Evento anómalo pero físicamente posible: sequía, ola de calor o poca luz.
        lectura = self.siguiente()
        anomalia = self.rnd.choice(["sequia", "calor", "oscuridad"])
        if anomalia == "sequia":
            lectura["humedad"] = round(self.base["humedad"] * 0.3, 1)
        elif anomalia == "calor":
            lectura["temperatura"] = round(self.base["temperatura"] + 12, 1)
        else:
            lectura["luz"] = round(self.base["luz"] * 0.1, 1)
        return anomalia, lectura


def construir_envio(sensor, codigo, rnd, prob_fuera, prob_invalido, anterior):
    """Devuelve (tipo, cuerpo). El tipo solo es para el log del simulador."""
    ahora = datetime.now(timezone.utc).isoformat()
    sorteo = rnd.random()

    if sorteo < prob_invalido:
        tipo = rnd.choice(["sin_campo", "texto", "imposible", "fecha_mala", "futuro", "repetida"])
        cuerpo = {"dispositivo": codigo, "medida_en": ahora, **sensor.siguiente()}
        if tipo == "sin_campo":
            del cuerpo["temperatura"]
        elif tipo == "texto":
            cuerpo["humedad"] = "sensor-error"
        elif tipo == "imposible":
            cuerpo["humedad"] = 140
        elif tipo == "fecha_mala":
            cuerpo["medida_en"] = "ayer a las 3"
        elif tipo == "futuro":
            cuerpo["medida_en"] = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        elif tipo == "repetida" and anterior is not None:
            cuerpo = anterior  # reintento de red: misma marca de tiempo
        return "INVALIDO:" + tipo, cuerpo

    if sorteo < prob_invalido + prob_fuera:
        anomalia, lectura = sensor.fuera_de_rango()
        return "FUERA_DE_RANGO:" + anomalia, {"dispositivo": codigo, "medida_en": ahora, **lectura}

    return "NORMAL", {"dispositivo": codigo, "medida_en": ahora, **sensor.siguiente()}


def enviar(url, token, cuerpo):
    peticion = urllib.request.Request(
        url,
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(peticion, timeout=5) as respuesta:
            return respuesta.status, json.loads(respuesta.read() or b"{}")
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read() or b"{}")
        except json.JSONDecodeError:
            return error.code, {}


def main():
    parser = argparse.ArgumentParser(description="Simulador del ESP32 de la matera inteligente.")
    parser.add_argument("--url", default="http://localhost:5000", help="URL base del backend")
    parser.add_argument("--matera", help="Archivo JSON generado por 'flask fabricar-matera'")
    parser.add_argument("--tocar-nfc", action="store_true", help="Abrir la URL del sticker NFC en el navegador")
    parser.add_argument("--codigo", help="Código del dispositivo, ej. ESP32-01")
    parser.add_argument("--token", default=os.environ.get("MATERA_TOKEN_DISPOSITIVO"),
                        help="Token del dispositivo (o variable MATERA_TOKEN_DISPOSITIVO)")
    parser.add_argument("--intervalo", type=float, default=5, help="Segundos entre lecturas (default 5)")
    parser.add_argument("--cantidad", type=int, default=0, help="Lecturas a enviar; 0 = sin fin")
    parser.add_argument("--perfil", choices=sorted(PERFILES), help="Condiciones típicas a simular (default: la especie de la matera, o potos)")
    parser.add_argument("--prob-fuera", type=float, default=0.15, help="Probabilidad de lectura fuera de rango")
    parser.add_argument("--prob-invalido", type=float, default=0.10, help="Probabilidad de dato inválido")
    parser.add_argument("--semilla", type=int, help="Semilla aleatoria (para repetir una corrida)")
    args = parser.parse_args()

    url_sticker = None
    if args.matera:
        with open(args.matera, encoding="utf-8") as archivo:
            matera = json.load(archivo)
        args.codigo = args.codigo or matera["codigo"]
        args.token = args.token or matera["token_firmware"]
        args.perfil = args.perfil or matera.get("especie")
        url_sticker = matera.get("url_sticker_nfc")
    args.perfil = args.perfil if args.perfil in PERFILES else "potos"

    if not args.codigo:
        parser.error("falta el código: usa --codigo o --matera")
    if not args.token:
        parser.error("falta el token: usa --token, --matera o la variable MATERA_TOKEN_DISPOSITIVO")
    if args.tocar_nfc:
        if not url_sticker:
            parser.error("--tocar-nfc necesita --matera (de ahí sale la URL del sticker)")
        print(f"📱 Teléfono acercado al sticker NFC de {args.codigo}: abriendo {url_sticker}")
        webbrowser.open(url_sticker)

    rnd = random.Random(args.semilla)
    sensor = SensorSimulado(PERFILES[args.perfil], rnd)
    url = f"{args.url.rstrip('/')}/api/dispositivos/{args.codigo}/lecturas"
    print(f"Simulando {args.codigo} (perfil {args.perfil}) -> {url} cada {args.intervalo}s. Ctrl+C para salir.")

    enviadas, anterior = 0, None
    try:
        while args.cantidad == 0 or enviadas < args.cantidad:
            tipo, cuerpo = construir_envio(sensor, args.codigo, rnd, args.prob_fuera, args.prob_invalido, anterior)
            try:
                status, respuesta = enviar(url, args.token, cuerpo)
            except (urllib.error.URLError, TimeoutError) as error:
                print(f"[{datetime.now():%H:%M:%S}] sin conexión con el backend: {error}")
            else:
                if status == 201:
                    anterior = cuerpo
                    detalle = respuesta.get("estado")
                elif respuesta.get("error") == "MATERA_SIN_DUENO":
                    detalle = "esperando a que alguien toque el sticker NFC y reclame la matera..."
                else:
                    detalle = f"{respuesta.get('error')}: {respuesta.get('mensaje')}"
                valores = {k: cuerpo.get(k) for k in ("humedad", "luz", "temperatura")}
                print(f"[{datetime.now():%H:%M:%S}] {tipo:<26} {valores} -> {status} {detalle}")
            enviadas += 1
            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print(f"\nSimulador detenido tras {enviadas} envíos.")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
