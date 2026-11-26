import requests


class ErrorApi(Exception):
    def __init__(self, mensaje, status=None, codigo=None):
        super().__init__(mensaje)
        self.status = status
        self.codigo = codigo


class ClienteFabrica:
    """Habla con las rutas /api/fabrica/* del backend usando la clave de fábrica."""

    def __init__(self, url_api, clave, timeout=10):
        self.url = url_api.rstrip("/")
        self.sesion = requests.Session()
        self.sesion.headers["X-Fabrica-Clave"] = clave
        self.timeout = timeout

    def _llamar(self, metodo, ruta, **kwargs):
        try:
            respuesta = self.sesion.request(metodo, f"{self.url}{ruta}", timeout=self.timeout, **kwargs)
        except requests.RequestException as error:
            raise ErrorApi(f"No se pudo contactar el backend en {self.url}: {error}") from error
        if respuesta.status_code >= 400:
            try:
                cuerpo = respuesta.json()
            except ValueError:
                raise ErrorApi(respuesta.text or f"HTTP {respuesta.status_code}", respuesta.status_code)
            raise ErrorApi(cuerpo.get("mensaje", respuesta.text), respuesta.status_code, cuerpo.get("error"))
        return respuesta.json() if respuesta.content else None

    def fabricar(self, especie, codigo=None, rfid_uid=None):
        cuerpo = {"especie": especie}
        if codigo:
            cuerpo["codigo"] = codigo
        if rfid_uid:
            cuerpo["rfid_uid"] = rfid_uid
        return self._llamar("POST", "/api/fabrica/materas", json=cuerpo)

    def identificar(self, rfid_uid):
        return self._llamar("GET", f"/api/fabrica/materas/rfid/{rfid_uid}")

    def descartar(self, codigo):
        return self._llamar("DELETE", f"/api/fabrica/materas/{codigo}")
