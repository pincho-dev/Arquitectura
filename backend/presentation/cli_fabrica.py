"""
Adaptador de entrada por línea de comandos: simula la fábrica de materas.

    flask --app presentation.app fabricar-matera --especie potos --cantidad 2

Por cada matera registra el dispositivo sin dueño y escribe
materas_fabricadas/<CODIGO>.json con lo que en la vida real iría grabado:
el token en el firmware del ESP32 y la URL de reclamo en el QR de la etiqueta.
Sin lector RFID: la matera queda sin tarjeta (para eso está fabrica/estacion.py).
El simulador del ESP32 lee ese archivo.
"""
import json
import secrets
from pathlib import Path

import click

from domain.plantas import CodigoDispositivoEnUso
from domain.puertos import EspecieNoEncontrada
from presentation.reclamo import url_reclamo

CARPETA_SALIDA = Path(__file__).resolve().parents[2] / "materas_fabricadas"


def registrar_cli_fabrica(app, fabricar_matera, url_front):

    @app.cli.command("fabricar-matera")
    @click.option("--especie", required=True, help="Especie del kit (ej. potos)")
    @click.option("--codigo", help="Código de la matera; si no se da, se genera uno")
    @click.option("--cantidad", default=1, show_default=True, help="Cuántas materas fabricar")
    def fabricar(especie, codigo, cantidad):
        CARPETA_SALIDA.mkdir(exist_ok=True)
        for _ in range(cantidad if not codigo else 1):
            codigo_matera = codigo or f"MAT-{secrets.token_hex(2).upper()}"
            try:
                dispositivo, token, clave = fabricar_matera.ejecutar(codigo_matera, especie)
            except (CodigoDispositivoEnUso, EspecieNoEncontrada) as error:
                raise click.ClickException(str(error))

            url = url_reclamo(url_front, dispositivo.codigo, clave)
            archivo = CARPETA_SALIDA / f"{dispositivo.codigo}.json"
            archivo.write_text(json.dumps({
                "codigo": dispositivo.codigo,
                "especie": dispositivo.especie,
                "token_firmware": token,
                "url_reclamo": url,
            }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            click.echo(f"Matera {dispositivo.codigo} ({dispositivo.especie}) fabricada")
            click.echo(f"  QR reclamo:  {url}")
            click.echo(f"  firmware:    {archivo}")
