"""
Lectores NFC de la estación de fábrica.

  LectorNfcUsb       lector USB real (ACR122U u otro compatible con nfcpy)
  LectorNfcSimulado  sin hardware, para probar el flujo de punta a punta

Ambos exponen la misma operación: grabar_url(url) -> uid del sticker.
Graba un único registro NDEF tipo URI, que es lo que el iPhone y Android
abren solos al acercar el celular.
"""

import secrets


class ErrorDeGrabacion(Exception):
    pass


class StickerNoVirgen(ErrorDeGrabacion):
    pass


class LectorNfcUsb:
    def __init__(self, dispositivo="usb", forzar=False, bloquear=False):
        try:
            import nfc  # import tardío: el modo simulado no necesita nfcpy
        except ImportError as error:
            raise SystemExit("Falta nfcpy: pip install -r requirements.txt") from error
        try:
            self.clf = nfc.ContactlessFrontend(dispositivo)
        except OSError as error:
            raise SystemExit(
                f"No se encontró el lector NFC en '{dispositivo}'. Revisa el cable y la sección "
                f"'Lector USB' del README de fabrica/. Detalle: {error}"
            ) from error
        self.forzar = forzar
        self.bloquear = bloquear

    def descripcion(self):
        return str(self.clf)

    def grabar_url(self, url):
        import ndef

        tag = self.clf.connect(rdwr={"on-connect": lambda t: False})
        if tag is None:  # Ctrl+C mientras esperaba
            raise KeyboardInterrupt
        uid = tag.identifier.hex().upper()

        if tag.ndef is None:
            # Algunos stickers vienen sin formato NDEF de fábrica.
            if not (hasattr(tag, "format") and tag.format()):
                raise ErrorDeGrabacion(f"No se pudo formatear el sticker {uid} ({tag.type}). ¿Es NTAG213/215/216?")
            tag = self.clf.connect(rdwr={"on-connect": lambda t: False})
            if tag is None or tag.ndef is None:
                raise ErrorDeGrabacion(f"El sticker {uid} no quedó con formato NDEF.")

        if tag.ndef.records and not self.forzar:
            raise StickerNoVirgen(
                f"El sticker {uid} ya tiene datos grabados. Usa uno virgen, o --forzar para sobrescribirlo."
            )
        if not tag.ndef.is_writeable:
            raise ErrorDeGrabacion(f"El sticker {uid} está bloqueado contra escritura.")

        registro = ndef.UriRecord(url)
        tamano = len(b"".join(ndef.message_encoder([registro])))
        if tamano > tag.ndef.capacity:
            raise ErrorDeGrabacion(
                f"La URL ocupa {tamano} bytes y el sticker solo tiene {tag.ndef.capacity}."
            )

        try:
            tag.ndef.records = [registro]
        except Exception as error:  # nfcpy lanza varios tipos según el chip
            raise ErrorDeGrabacion(f"Falló la escritura (¿se movió el sticker?): {error}") from error

        # Verificación: releer lo que quedó grabado.
        releido = self.clf.connect(rdwr={"on-connect": lambda t: False})
        if releido is None or releido.ndef is None or not releido.ndef.records:
            raise ErrorDeGrabacion("No se pudo releer el sticker después de grabarlo.")
        if releido.identifier.hex().upper() != uid:
            raise ErrorDeGrabacion("Se cambió el sticker durante la grabación.")
        if getattr(releido.ndef.records[0], "iri", None) != url:
            raise ErrorDeGrabacion("La URL releída no coincide con la grabada.")

        if self.bloquear:
            # IRREVERSIBLE: el sticker queda de solo lectura para siempre.
            if not releido.protect():
                raise ErrorDeGrabacion("El sticker se grabó bien pero no se pudo bloquear.")

        return uid

    def esperar_retiro(self):
        # on-connect -> True hace que nfcpy espere a que el sticker se retire.
        self.clf.connect(rdwr={"on-connect": lambda t: True})

    def cerrar(self):
        self.clf.close()


class LectorNfcSimulado:
    """Hace lo mismo sin hardware: inventa un UID tipo NTAG (7 bytes, empieza en 04)."""

    def __init__(self):
        self.grabados = []

    def descripcion(self):
        return "lector simulado (sin hardware)"

    def grabar_url(self, url):
        uid = "04" + secrets.token_hex(6).upper()
        self.grabados.append((uid, url))
        return uid

    def esperar_retiro(self):
        pass

    def cerrar(self):
        pass
