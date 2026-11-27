"""Galería de fotos: el procesador con Pillow (imágenes reales en memoria), el
almacén en una carpeta temporal y los casos de uso y la API con dobles: sin BD."""
import io
from datetime import datetime, timezone

import pytest
from flask import Flask
from PIL import Image

from application.fotos import EliminarFoto, ListarFotos, SubirFoto, VerFoto
from domain.fotos import LADO_MAXIMO_PX, DatosDeFotoInvalidos, Foto, FotoNoEncontrada, ImagenInvalida
from domain.plantas import AccesoDenegado, Lectura, PlantaNoEncontrada
from domain.puertos import RepositorioFotos
from infrastructure.almacen_fotos_disco import AlmacenFotosDisco
from infrastructure.procesador_imagenes_pillow import ProcesadorImagenesPillow
from infrastructure.tokens_jwt import TokensJwt
from presentation.api_fotos import crear_api_fotos
from presentation.seguridad import crear_requiere_usuario
from tests.test_plantas import AJENO, DUENA, _HistorialFalso, _RepositorioPlantasFalso

CODUENO = 3
AHORA = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
GPS_DE_LA_CASA = {2: (4.0, 42.0, 0.0), 4: (74.0, 3.0, 0.0)}  # latitud y longitud


def _jpeg_con_gps(ancho=400, alto=200, orientacion=6):
    imagen = Image.new("RGB", (ancho, alto), (30, 140, 60))
    exif = Image.Exif()
    exif[0x0112] = orientacion          # Orientation: 6 = girar 90° a la derecha
    exif[0x0110] = "Telefono de Ana"    # Model
    exif[0x8825] = GPS_DE_LA_CASA        # GPSInfo
    salida = io.BytesIO()
    imagen.save(salida, "JPEG", exif=exif)
    return salida.getvalue()


def _png(ancho=50, alto=50, modo="RGBA"):
    salida = io.BytesIO()
    Image.new(modo, (ancho, alto)).save(salida, "PNG")
    return salida.getvalue()


# ------------------------------------------------------ procesador (Pillow)

def test_quita_el_exif_con_el_gps_y_endereza_la_foto():
    original = _jpeg_con_gps()
    assert Image.open(io.BytesIO(original)).getexif().get(0x8825)  # el original sí trae GPS

    limpia = ProcesadorImagenesPillow().normalizar(original)

    resultado = Image.open(io.BytesIO(limpia.contenido))
    assert resultado.format == "WEBP" and limpia.tipo == "image/webp"
    assert len(resultado.getexif()) == 0
    assert "exif" not in resultado.info and "xmp" not in resultado.info
    assert b"Telefono de Ana" not in limpia.contenido
    # Orientación 6: la foto horizontal guardada "de lado" queda vertical.
    assert (limpia.ancho, limpia.alto) == (200, 400) == resultado.size


def test_reduce_las_fotos_grandes_sin_deformarlas():
    limpia = ProcesadorImagenesPillow().normalizar(_jpeg_con_gps(4000, 3000, orientacion=1))

    assert (limpia.ancho, limpia.alto) == (LADO_MAXIMO_PX, 1200)


def test_png_con_transparencia_se_conserva():
    limpia = ProcesadorImagenesPillow().normalizar(_png())

    assert Image.open(io.BytesIO(limpia.contenido)).mode == "RGBA"


def _gif():
    salida = io.BytesIO()
    Image.new("RGB", (10, 10)).save(salida, "GIF")
    return salida.getvalue()


@pytest.mark.parametrize("contenido", [
    b"<?php system($_GET['c']); ?>",          # un "jpg" que no es imagen
    b"\x89PNG\r\n\x1a\n" + b"\x00" * 40,       # cabecera de PNG y nada más
    _jpeg_con_gps()[:300],                     # JPEG cortado a la mitad
    _gif(),                                    # formato no permitido
    _png(8000, 6000, modo="1"),                # 48 MP: bomba de descompresión (pesa pocos KB)
], ids=["texto", "cabecera-falsa", "jpeg-cortado", "gif", "bomba"])
def test_rechaza_lo_que_no_es_una_foto_permitida(contenido):
    with pytest.raises(ImagenInvalida):
        ProcesadorImagenesPillow().normalizar(contenido)


# --------------------------------------------------------------- almacén

def test_almacen_guarda_abre_y_borra(tmp_path):
    almacen = AlmacenFotosDisco(tmp_path)
    clave = "a" * 32

    almacen.guardar(clave, b"foto")
    assert almacen.abrir(clave) == b"foto"
    almacen.eliminar(clave)
    assert almacen.abrir(clave) is None
    almacen.eliminar(clave)  # borrar dos veces no falla


@pytest.mark.parametrize("clave", ["../../.env", "/etc/passwd", "A" * 32, ""])
def test_almacen_no_acepta_claves_que_salgan_de_la_carpeta(tmp_path, clave):
    almacen = AlmacenFotosDisco(tmp_path / "fotos")

    assert almacen.abrir(clave) is None
    with pytest.raises(ValueError):
        almacen.guardar(clave, b"x")


# ------------------------------------------------------------ casos de uso

class _AlmacenFalso:
    def __init__(self):
        self.archivos = {}

    def guardar(self, clave, contenido):
        self.archivos[clave] = contenido

    def abrir(self, clave):
        return self.archivos.get(clave)

    def eliminar(self, clave):
        self.archivos.pop(clave, None)


class _RepositorioFotosFalso(RepositorioFotos):
    def __init__(self, repositorio_plantas, falla_al_crear=False):
        self.repositorio_plantas = repositorio_plantas
        self.fotos = {}
        self.falla_al_crear = falla_al_crear

    def crear(self, planta_id, autor_id, clave_archivo, tipo, ancho, alto, descripcion, lectura):
        if self.falla_al_crear:
            raise RuntimeError("la BD se cayó")
        planta = self.repositorio_plantas.buscar(planta_id)
        foto = Foto(len(self.fotos) + 1, planta_id, planta.nombre, planta.especie, autor_id, f"Usuario {autor_id}",
                    clave_archivo, tipo, ancho, alto, descripcion,
                    None if lectura is None else {"estado": lectura.estado, "humedad": lectura.humedad,
                                                  "luz": lectura.luz, "temperatura": lectura.temperatura,
                                                  "medida_en": lectura.medida_en},
                    AHORA, planta.duenos)
        self.fotos[foto.id] = foto
        return foto

    def buscar(self, foto_id):
        return self.fotos.get(foto_id)

    def listar(self, limite, antes_de=None, planta_id=None):
        fotos = sorted(self.fotos.values(), key=lambda f: f.id, reverse=True)
        fotos = [f for f in fotos if (antes_de is None or f.id < antes_de)
                 and (planta_id is None or f.planta_id == planta_id)]
        return fotos[:limite]

    def eliminar(self, foto_id):
        self.fotos.pop(foto_id, None)


@pytest.fixture
def entorno():
    plantas, historial = _RepositorioPlantasFalso(), _HistorialFalso()
    planta = plantas.crear("Pepa", "potos", DUENA)
    plantas.agregar_dueno(planta.id, CODUENO)
    historial.guardar(Lectura(planta.id, 55, 600, 22, "SALUDABLE", AHORA, "dispositivo", 9))
    fotos, almacen = _RepositorioFotosFalso(plantas), _AlmacenFalso()
    subir = SubirFoto(plantas, historial, fotos, almacen, ProcesadorImagenesPillow())
    return plantas, fotos, almacen, subir, planta


def test_subir_guarda_la_foto_limpia_con_la_ultima_lectura(entorno):
    _, fotos, almacen, subir, planta = entorno

    foto = subir.ejecutar(DUENA, planta.id, _jpeg_con_gps(), "  Le salió hoja nueva  ")

    assert foto.descripcion == "Le salió hoja nueva"
    assert foto.lectura["estado"] == "SALUDABLE" and foto.lectura["humedad"] == 55
    guardado = almacen.archivos[foto.clave_archivo]
    assert Image.open(io.BytesIO(guardado)).format == "WEBP"
    assert len(foto.clave_archivo) == 32


def test_solo_un_dueno_sube_fotos_a_su_planta(entorno):
    _, _, almacen, subir, planta = entorno

    with pytest.raises(AccesoDenegado):
        subir.ejecutar(AJENO, planta.id, _jpeg_con_gps())
    with pytest.raises(PlantaNoEncontrada):
        subir.ejecutar(DUENA, 999, _jpeg_con_gps())
    assert almacen.archivos == {}


def test_descripcion_larga_o_archivo_vacio_se_rechazan(entorno):
    _, _, _, subir, planta = entorno

    with pytest.raises(DatosDeFotoInvalidos):
        subir.ejecutar(DUENA, planta.id, _jpeg_con_gps(), "x" * 281)
    with pytest.raises(ImagenInvalida):
        subir.ejecutar(DUENA, planta.id, b"")


def test_si_falla_la_bd_no_queda_el_archivo_huerfano(entorno):
    plantas, _, almacen, _, planta = entorno
    historial = _HistorialFalso()
    subir = SubirFoto(plantas, historial, _RepositorioFotosFalso(plantas, falla_al_crear=True), almacen,
                      ProcesadorImagenesPillow())

    with pytest.raises(RuntimeError):
        subir.ejecutar(DUENA, planta.id, _jpeg_con_gps())
    assert almacen.archivos == {}


def test_borra_el_autor_o_un_dueno_pero_no_un_extrano(entorno):
    _, fotos, almacen, subir, planta = entorno
    primera = subir.ejecutar(DUENA, planta.id, _png())
    segunda = subir.ejecutar(DUENA, planta.id, _png())
    eliminar = EliminarFoto(fotos, almacen)

    with pytest.raises(AccesoDenegado):
        eliminar.ejecutar(AJENO, primera.id)
    eliminar.ejecutar(DUENA, primera.id)
    eliminar.ejecutar(CODUENO, segunda.id)

    assert fotos.fotos == {} and almacen.archivos == {}
    with pytest.raises(FotoNoEncontrada):
        VerFoto(fotos, almacen).ejecutar(primera.id)


def test_listar_de_la_mas_nueva_a_la_mas_vieja_con_cursor(entorno):
    _, fotos, _, subir, planta = entorno
    ids = [subir.ejecutar(DUENA, planta.id, _png()).id for _ in range(5)]
    listar = ListarFotos(fotos)

    pagina = listar.ejecutar(2)
    siguiente = listar.ejecutar(2, antes_de=pagina[-1].id)

    assert [f.id for f in pagina + siguiente] == ids[::-1][:4]


# ------------------------------------------------------------------- API

@pytest.fixture
def api(entorno):
    _, fotos, almacen, subir, planta = entorno
    tokens = TokensJwt("s" * 40)
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
    app.register_blueprint(crear_api_fotos(
        subir, ListarFotos(fotos), VerFoto(fotos, almacen), EliminarFoto(fotos, almacen), crear_requiere_usuario(tokens),
    ))
    cabecera = {u: {"Authorization": f"Bearer {tokens.emitir_para_usuario(u)}"} for u in (DUENA, AJENO)}
    return app.test_client(), cabecera, planta


def _subir(client, cabecera, planta_id, contenido, nombre="foto.jpg", **campos):
    datos = {"foto": (io.BytesIO(contenido), nombre), **campos}
    return client.post(f"/api/plantas/{planta_id}/fotos", data=datos, headers=cabecera,
                       content_type="multipart/form-data")


def test_api_subir_listar_ver_y_borrar(api):
    client, cabecera, planta = api

    creada = _subir(client, cabecera[DUENA], planta.id, _jpeg_con_gps(), descripcion="¡Mírenla!")
    assert creada.status_code == 201
    cuerpo = creada.get_json()
    assert cuerpo["planta"]["nombre"] == "Pepa"
    assert cuerpo["lectura"]["estado_texto"] == "Saludable"
    assert cuerpo["puede_borrar"] is True

    galeria = client.get("/api/fotos", headers=cabecera[AJENO]).get_json()
    assert [f["id"] for f in galeria] == [cuerpo["id"]]
    assert galeria[0]["puede_borrar"] is False

    imagen = client.get(cuerpo["imagen_url"], headers=cabecera[AJENO])
    assert imagen.status_code == 200
    assert imagen.mimetype == "image/webp"
    assert imagen.headers["X-Content-Type-Options"] == "nosniff"
    assert len(Image.open(io.BytesIO(imagen.data)).getexif()) == 0

    assert client.delete(f"/api/fotos/{cuerpo['id']}", headers=cabecera[AJENO]).status_code == 403
    assert client.delete(f"/api/fotos/{cuerpo['id']}", headers=cabecera[DUENA]).status_code == 204
    assert client.get(cuerpo["imagen_url"], headers=cabecera[DUENA]).status_code == 404


def test_api_errores_al_subir(api):
    client, cabecera, planta = api

    falsa = _subir(client, cabecera[DUENA], planta.id, b"no soy una foto", nombre="gato.jpg")
    assert falsa.status_code == 400 and falsa.get_json()["error"] == "IMAGEN_INVALIDA"

    sin_archivo = client.post(f"/api/plantas/{planta.id}/fotos", data={}, headers=cabecera[DUENA],
                              content_type="multipart/form-data")
    assert sin_archivo.status_code == 400

    ajena = _subir(client, cabecera[AJENO], planta.id, _png())
    assert ajena.status_code == 403

    enorme = _subir(client, cabecera[DUENA], planta.id, b"\xff" * (2 * 1024 * 1024))
    assert enorme.status_code == 413

    assert client.get("/api/fotos?limite=muchas", headers=cabecera[DUENA]).status_code == 400
    assert client.get("/api/fotos").status_code == 401
