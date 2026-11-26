from urllib.parse import urlencode


def url_reclamo(url_front, codigo, clave):
    """URL del QR que va impreso en la etiqueta de la matera: abre la página de
    reclamo con el código y la clave. Es lo único que lleva el QR; el token
    del ESP32 nunca sale del firmware."""
    return f"{url_front.rstrip('/')}/reclamar.html?" + urlencode({"codigo": codigo, "clave": clave})
