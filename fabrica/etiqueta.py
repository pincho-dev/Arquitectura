"""Etiqueta que se imprime y se pega en la matera: el QR con la URL de reclamo,
el código y la clave (por si el celular no puede escanear el QR).

La clave de reclamo va SOLO aquí, impresa. El token del ESP32 nunca sale del
firmware y la tarjeta RFID solo identifica la matera dentro de la fábrica.
"""
from urllib.parse import parse_qs, urlparse


def clave_de(url_reclamo):
    return parse_qs(urlparse(url_reclamo).query).get("clave", [""])[0]


def qr_en_terminal(url):
    """Dibuja el QR en la consola: se puede escanear directo de la pantalla."""
    import io
    import qrcode
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    salida = io.StringIO()
    qr.print_ascii(out=salida, invert=True)
    return salida.getvalue()


def generar_etiqueta(carpeta, matera):
    import qrcode
    from PIL import Image, ImageDraw, ImageFont

    carpeta.mkdir(parents=True, exist_ok=True)
    qr = qrcode.make(matera["url_reclamo"], box_size=8, border=2).convert("RGB")
    lineas = [
        f"{matera['codigo']}  ·  {matera['especie']}",
        f"clave: {clave_de(matera['url_reclamo'])}",
        f"RFID {matera.get('rfid_uid') or '-'}",
    ]
    try:
        fuente = ImageFont.load_default(size=20)
    except TypeError:            # Pillow < 10.1
        fuente = ImageFont.load_default()

    alto_texto = 30 * len(lineas) + 10
    etiqueta = Image.new("RGB", (qr.width, qr.height + alto_texto), "white")
    etiqueta.paste(qr, (0, 0))
    dibujo = ImageDraw.Draw(etiqueta)
    for i, linea in enumerate(lineas):
        ancho = dibujo.textlength(linea, font=fuente)
        dibujo.text(((qr.width - ancho) / 2, qr.height + 5 + 30 * i), linea, fill="black", font=fuente)

    archivo = carpeta / f"{matera['codigo']}_etiqueta.png"
    etiqueta.save(archivo)
    return archivo
