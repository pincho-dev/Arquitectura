from urllib.parse import urlencode


def url_sticker(url_front, codigo, clave):
    """URL que se graba en el sticker NFC de la matera: abre la página de
    reclamo con el código y la clave. Es lo único que lleva el sticker; el
    token del ESP32 nunca sale del firmware."""
    return f"{url_front.rstrip('/')}/reclamar.html?" + urlencode({"codigo": codigo, "clave": clave})
