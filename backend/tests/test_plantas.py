"""Casos de uso de plantas, lecturas y dispositivos con dobles de prueba:
sin servidor, sin archivos y sin base de datos."""
from datetime import datetime, timedelta, timezone

import pytest

from application.consultar_plantas import ConsultarEstadoPlanta, ListarPlantas
from application.crear_planta import CrearPlanta
from application.diagnosticar_planta import DiagnosticarPlanta
from application.compartir_planta import CompartirPlanta
from application.materas import FabricarMatera, ReclamarMatera
from application.registrar_lectura import RegistrarLectura
from application.vincular_dispositivo import VincularDispositivo
from domain.modelos import RangosEspecie, ValorFueraDeRangoFisico
from domain.plantas import (
    AccesoDenegado, ClaveDeReclamoInvalida, DatosDePlantaInvalidos, Dispositivo, InvitadoNoRegistrado, LecturaDuplicada,
    MateraSinDueno, MateraYaReclamada, Planta, PlantaNoEncontrada,
)
from domain.puertos import (
    EspecieLookup, EspecieNoEncontrada, GeneradorTokensDispositivo, HistorialLecturas,
    RepositorioDispositivos, RepositorioPlantas,
)
from domain.valores import Rango
from tests.test_autenticacion import _RepositorioUsuariosFalso

DUENA, AJENO = 1, 2
AHORA = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)


class _EspecieLookupFalso(EspecieLookup):
    def obtener_rangos(self, nombre_especie):
        if nombre_especie != "potos":
            raise EspecieNoEncontrada(nombre_especie)
        return RangosEspecie("potos", Rango(40, 70), Rango(300, 1200), Rango(18, 30))


class _RepositorioPlantasFalso(RepositorioPlantas):
    def __init__(self):
        self.plantas = {}

    def crear(self, nombre, especie, usuario_id):
        _EspecieLookupFalso().obtener_rangos(especie)
        planta = Planta(len(self.plantas) + 1, nombre, especie, {usuario_id})
        self.plantas[planta.id] = planta
        return planta

    def buscar(self, planta_id):
        return self.plantas.get(planta_id)

    def listar_de_usuario(self, usuario_id):
        return [p for p in self.plantas.values() if usuario_id in p.duenos]

    def eliminar(self, planta_id):
        self.plantas.pop(planta_id, None)

    def agregar_dueno(self, planta_id, usuario_id):
        planta = self.plantas[planta_id]
        self.plantas[planta_id] = Planta(planta.id, planta.nombre, planta.especie, planta.duenos | {usuario_id})


class _HistorialFalso(HistorialLecturas):
    def __init__(self):
        self.lecturas = []

    def guardar(self, lectura):
        if lectura.dispositivo_id is not None and any(
            l.dispositivo_id == lectura.dispositivo_id and l.medida_en == lectura.medida_en for l in self.lecturas
        ):
            raise LecturaDuplicada()
        self.lecturas.append(lectura)

    def ultima(self, planta_id):
        recientes = self.listar(planta_id, 1)
        return recientes[0] if recientes else None

    def listar(self, planta_id, limite):
        propias = [l for l in self.lecturas if l.planta_id == planta_id]
        return sorted(propias, key=lambda l: l.medida_en, reverse=True)[:limite]


class _RepositorioDispositivosFalso(RepositorioDispositivos):
    def __init__(self):
        self.dispositivos = []
        self.claves = {}

    def registrar(self, codigo, planta_id, token):
        dispositivo = Dispositivo(len(self.dispositivos) + 1, codigo, planta_id)
        self.dispositivos.append(dispositivo)
        return dispositivo

    def listar_de_planta(self, planta_id):
        return [d for d in self.dispositivos if d.planta_id == planta_id]

    def registrar_de_fabrica(self, codigo, especie, token, clave_reclamo):
        _EspecieLookupFalso().obtener_rangos(especie)
        dispositivo = self.registrar(codigo, None, token)
        dispositivo.especie = especie
        self.claves[codigo] = clave_reclamo
        return dispositivo

    def buscar_para_reclamo(self, codigo, clave_reclamo):
        if self.claves.get(codigo) != clave_reclamo:
            return None
        return next(d for d in self.dispositivos if d.codigo == codigo)

    def asignar_planta(self, dispositivo_id, planta_id):
        dispositivo = next(d for d in self.dispositivos if d.id == dispositivo_id)
        if dispositivo.planta_id is not None:
            return False
        dispositivo.planta_id = planta_id
        return True


class _GeneradorFalso(GeneradorTokensDispositivo):
    def generar(self):
        return "dev_token_de_prueba"

    def generar_clave_reclamo(self):
        return "clave-sticker"


@pytest.fixture
def entorno():
    plantas, historial, dispositivos = _RepositorioPlantasFalso(), _HistorialFalso(), _RepositorioDispositivosFalso()
    diagnosticar = DiagnosticarPlanta(_EspecieLookupFalso())
    planta = plantas.crear("Potos sala", "potos", DUENA)
    return {
        "planta": planta,
        "historial": historial,
        "registrar": RegistrarLectura(plantas, historial, diagnosticar),
        "consultar": ConsultarEstadoPlanta(plantas, historial, dispositivos, diagnosticar),
        "listar": ListarPlantas(plantas, historial, dispositivos, diagnosticar),
        "crear": CrearPlanta(plantas),
        "vincular": VincularDispositivo(plantas, dispositivos, _GeneradorFalso()),
    }


# ---------------------------------------------------------------- dominio

def test_solo_los_duenos_tienen_acceso_a_la_planta():
    planta = Planta(1, "Potos", "potos", {DUENA})

    planta.verificar_acceso(DUENA)
    with pytest.raises(AccesoDenegado):
        planta.verificar_acceso(AJENO)


def test_dispositivo_conectado_solo_si_reporto_hace_poco():
    assert Dispositivo(1, "ESP32-01", 1, AHORA - timedelta(seconds=30)).esta_conectado(AHORA)
    assert not Dispositivo(1, "ESP32-01", 1, AHORA - timedelta(minutes=10)).esta_conectado(AHORA)
    assert not Dispositivo(1, "ESP32-01", 1, None).esta_conectado(AHORA)


# -------------------------------------------------------- registrar lectura

def test_lectura_en_rango_se_guarda_como_saludable(entorno):
    diagnostico = entorno["registrar"].desde_formulario(DUENA, entorno["planta"].id, 55, 500, 22, AHORA)

    assert diagnostico.estado == "SALUDABLE"
    guardada = entorno["historial"].lecturas[0]
    assert (guardada.estado, guardada.origen, guardada.dispositivo_id) == ("SALUDABLE", "formulario", None)


def test_lectura_fuera_de_rango_se_guarda_con_su_estado(entorno):
    diagnostico = entorno["registrar"].desde_formulario(DUENA, entorno["planta"].id, 10, 500, 22, AHORA)

    assert diagnostico.estado == "CRITICO"
    assert entorno["historial"].lecturas[0].estado == "CRITICO"


def test_lectura_fisicamente_imposible_se_rechaza_y_no_se_guarda(entorno):
    with pytest.raises(ValorFueraDeRangoFisico):
        entorno["registrar"].desde_formulario(DUENA, entorno["planta"].id, 150, 500, 22, AHORA)

    assert entorno["historial"].lecturas == []


def test_usuario_ajeno_no_puede_registrar_lecturas(entorno):
    with pytest.raises(AccesoDenegado):
        entorno["registrar"].desde_formulario(AJENO, entorno["planta"].id, 55, 500, 22, AHORA)


def test_lectura_de_dispositivo_va_a_la_planta_del_dispositivo(entorno):
    dispositivo = Dispositivo(9, "ESP32-01", entorno["planta"].id)

    entorno["registrar"].desde_dispositivo(dispositivo, 55, 500, 22, AHORA)

    guardada = entorno["historial"].lecturas[0]
    assert (guardada.planta_id, guardada.origen, guardada.dispositivo_id) == (entorno["planta"].id, "dispositivo", 9)


def test_lectura_repetida_del_dispositivo_se_detecta(entorno):
    dispositivo = Dispositivo(9, "ESP32-01", entorno["planta"].id)
    entorno["registrar"].desde_dispositivo(dispositivo, 55, 500, 22, AHORA)

    with pytest.raises(LecturaDuplicada):
        entorno["registrar"].desde_dispositivo(dispositivo, 55, 500, 22, AHORA)


def test_lectura_para_planta_inexistente_falla(entorno):
    with pytest.raises(PlantaNoEncontrada):
        entorno["registrar"].desde_formulario(DUENA, 999, 55, 500, 22, AHORA)


# ------------------------------------------------------- consultar plantas

def test_estado_sin_lecturas_no_tiene_diagnostico(entorno):
    resumen = entorno["consultar"].ejecutar(DUENA, entorno["planta"].id)

    assert resumen.diagnostico is None
    assert resumen.ultima_lectura is None
    assert resumen.historial == []


def test_estado_usa_la_lectura_mas_reciente_y_trae_historial(entorno):
    registrar, planta_id = entorno["registrar"], entorno["planta"].id
    registrar.desde_formulario(DUENA, planta_id, 55, 500, 22, AHORA - timedelta(minutes=5))
    registrar.desde_formulario(DUENA, planta_id, 10, 500, 22, AHORA)

    resumen = entorno["consultar"].ejecutar(DUENA, planta_id)

    assert resumen.diagnostico.estado == "CRITICO"
    assert [l.humedad for l in resumen.historial] == [10, 55]


def test_usuario_ajeno_no_puede_ver_el_estado(entorno):
    with pytest.raises(AccesoDenegado):
        entorno["consultar"].ejecutar(AJENO, entorno["planta"].id)


def test_listar_devuelve_solo_las_plantas_del_usuario(entorno):
    entorno["crear"].ejecutar(AJENO, "Potos ajeno", "potos")

    nombres = [r.planta.nombre for r in entorno["listar"].ejecutar(DUENA)]

    assert nombres == ["Potos sala"]


# ------------------------------------------------- crear planta / vincular

def test_crear_planta_sin_nombre_falla(entorno):
    with pytest.raises(DatosDePlantaInvalidos):
        entorno["crear"].ejecutar(DUENA, "   ", "potos")


def test_crear_planta_de_especie_desconocida_falla(entorno):
    with pytest.raises(EspecieNoEncontrada):
        entorno["crear"].ejecutar(DUENA, "Rara", "monstera")


def test_vincular_dispositivo_devuelve_el_token_una_vez(entorno):
    dispositivo, token = entorno["vincular"].ejecutar(DUENA, entorno["planta"].id, " esp32-01 ")

    assert dispositivo.codigo == "ESP32-01"
    assert token == "dev_token_de_prueba"


def test_usuario_ajeno_no_puede_vincular_dispositivos(entorno):
    with pytest.raises(AccesoDenegado):
        entorno["vincular"].ejecutar(AJENO, entorno["planta"].id, "ESP32-99")


# -------------------------------------------- materas: fábrica y sticker NFC

@pytest.fixture
def fabrica():
    plantas, dispositivos, historial = _RepositorioPlantasFalso(), _RepositorioDispositivosFalso(), _HistorialFalso()
    return {
        "plantas": plantas,
        "historial": historial,
        "fabricar": FabricarMatera(dispositivos, _GeneradorFalso()),
        "reclamar": ReclamarMatera(dispositivos, plantas),
        "registrar": RegistrarLectura(plantas, historial, DiagnosticarPlanta(_EspecieLookupFalso())),
    }


def test_fabricar_matera_la_deja_sin_dueno_con_token_y_clave(fabrica):
    dispositivo, token, clave = fabrica["fabricar"].ejecutar("mat-01", "potos")

    assert dispositivo.codigo == "MAT-01"
    assert not dispositivo.tiene_dueno()
    assert (token, clave) == ("dev_token_de_prueba", "clave-sticker")


def test_matera_sin_dueno_no_puede_reportar_lecturas(fabrica):
    dispositivo, _, _ = fabrica["fabricar"].ejecutar("MAT-01", "potos")

    with pytest.raises(MateraSinDueno):
        fabrica["registrar"].desde_dispositivo(dispositivo, 55, 500, 22, AHORA)
    assert fabrica["historial"].lecturas == []


def test_reclamar_con_el_sticker_crea_la_planta_del_usuario(fabrica):
    fabrica["fabricar"].ejecutar("MAT-01", "potos")

    planta, dispositivo = fabrica["reclamar"].ejecutar(DUENA, "mat-01", "clave-sticker")

    assert (planta.nombre, planta.especie, planta.duenos) == ("Matera MAT-01", "potos", frozenset({DUENA}))
    assert dispositivo.planta_id == planta.id


def test_despues_de_reclamarla_la_matera_ya_puede_reportar(fabrica):
    dispositivo, _, _ = fabrica["fabricar"].ejecutar("MAT-01", "potos")
    planta, _ = fabrica["reclamar"].ejecutar(DUENA, "MAT-01", "clave-sticker")

    fabrica["registrar"].desde_dispositivo(dispositivo, 55, 500, 22, AHORA)

    assert fabrica["historial"].lecturas[0].planta_id == planta.id


def test_reclamar_permite_elegir_nombre_y_especie(fabrica):
    fabrica["fabricar"].ejecutar("MAT-01", "potos")

    planta, _ = fabrica["reclamar"].ejecutar(DUENA, "MAT-01", "clave-sticker", nombre="Mi potos", especie="Potos")

    assert planta.nombre == "Mi potos"


def test_sticker_con_clave_incorrecta_no_reclama_nada(fabrica):
    fabrica["fabricar"].ejecutar("MAT-01", "potos")

    with pytest.raises(ClaveDeReclamoInvalida):
        fabrica["reclamar"].ejecutar(DUENA, "MAT-01", "clave-adivinada")
    assert fabrica["plantas"].plantas == {}


def test_una_matera_reclamada_no_la_puede_reclamar_otro_usuario(fabrica):
    fabrica["fabricar"].ejecutar("MAT-01", "potos")
    fabrica["reclamar"].ejecutar(DUENA, "MAT-01", "clave-sticker")

    with pytest.raises(MateraYaReclamada):
        fabrica["reclamar"].ejecutar(AJENO, "MAT-01", "clave-sticker")
    assert fabrica["plantas"].listar_de_usuario(AJENO) == []


# ------------------------------------------------------- compartir planta

TERCERO = 3


@pytest.fixture
def compartida():
    plantas, historial, dispositivos = _RepositorioPlantasFalso(), _HistorialFalso(), _RepositorioDispositivosFalso()
    usuarios = _RepositorioUsuariosFalso()
    for nombre in ("duena", "ajeno", "tercero"):
        usuarios.crear(nombre, f"{nombre}@correo.com", "hash")  # ids 1, 2, 3
    diagnosticar = DiagnosticarPlanta(_EspecieLookupFalso())
    return {
        "planta": plantas.crear("Potos sala", "potos", DUENA),
        "compartir": CompartirPlanta(plantas, usuarios),
        "consultar": ConsultarEstadoPlanta(plantas, historial, dispositivos, diagnosticar),
        "listar": ListarPlantas(plantas, historial, dispositivos, diagnosticar),
        "registrar": RegistrarLectura(plantas, historial, diagnosticar),
        "usuarios": usuarios,
    }


def test_el_dueno_comparte_y_el_invitado_ve_la_planta(compartida):
    planta_id = compartida["planta"].id

    planta = compartida["compartir"].ejecutar(DUENA, planta_id, " AJENO@correo.com ")

    assert planta.duenos == frozenset({DUENA, AJENO})
    assert compartida["consultar"].ejecutar(AJENO, planta_id).planta.nombre == "Potos sala"
    assert [r.planta.id for r in compartida["listar"].ejecutar(AJENO)] == [planta_id]


def test_el_co_dueno_tambien_puede_registrar_lecturas(compartida):
    compartida["compartir"].ejecutar(DUENA, compartida["planta"].id, "ajeno@correo.com")

    diagnostico = compartida["registrar"].desde_formulario(AJENO, compartida["planta"].id, 55, 500, 22, AHORA)

    assert diagnostico.estado == "SALUDABLE"


def test_compartir_no_le_da_acceso_a_un_tercero(compartida):
    compartida["compartir"].ejecutar(DUENA, compartida["planta"].id, "ajeno@correo.com")

    with pytest.raises(AccesoDenegado):
        compartida["consultar"].ejecutar(TERCERO, compartida["planta"].id)


def test_quien_no_es_dueno_no_puede_compartir(compartida):
    with pytest.raises(AccesoDenegado):
        compartida["compartir"].ejecutar(AJENO, compartida["planta"].id, "tercero@correo.com")


def test_un_co_dueno_puede_volver_a_compartir(compartida):
    planta_id = compartida["planta"].id
    compartida["compartir"].ejecutar(DUENA, planta_id, "ajeno@correo.com")

    planta = compartida["compartir"].ejecutar(AJENO, planta_id, "tercero@correo.com")

    assert planta.duenos == frozenset({DUENA, AJENO, TERCERO})


def test_compartir_dos_veces_con_la_misma_persona_no_duplica(compartida):
    planta_id = compartida["planta"].id
    compartida["compartir"].ejecutar(DUENA, planta_id, "ajeno@correo.com")

    planta = compartida["compartir"].ejecutar(DUENA, planta_id, "ajeno@correo.com")

    assert planta.duenos == frozenset({DUENA, AJENO})


def test_compartir_con_correo_no_registrado_falla(compartida):
    with pytest.raises(InvitadoNoRegistrado):
        compartida["compartir"].ejecutar(DUENA, compartida["planta"].id, "nadie@correo.com")


def test_compartir_con_cuenta_inactiva_falla(compartida):
    compartida["usuarios"].por_email["ajeno@correo.com"].activo = False

    with pytest.raises(InvitadoNoRegistrado):
        compartida["compartir"].ejecutar(DUENA, compartida["planta"].id, "ajeno@correo.com")


def test_compartir_planta_inexistente_falla(compartida):
    with pytest.raises(PlantaNoEncontrada):
        compartida["compartir"].ejecutar(DUENA, 999, "ajeno@correo.com")
