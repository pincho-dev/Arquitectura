"""Amistades (para el ranking entre amigos) con dobles de prueba: sin BD."""
from datetime import datetime, timezone

import pytest
from flask import Flask

from application.amistades import AceptarAmistad, EliminarAmistad, ListarAmistades, SolicitarAmistad
from domain.amistades import (
    AmigoNoRegistrado, Amistad, AmistadNoEncontrada, SolicitudInvalida, SolicitudYaExiste, YaSonAmigos,
)
from domain.puertos import RepositorioAmistades
from infrastructure.tokens_jwt import TokensJwt
from presentation.api_liga import crear_api_amigos
from presentation.seguridad import crear_requiere_usuario
from tests.test_autenticacion import _RepositorioUsuariosFalso

AHORA = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)


class _RepositorioAmistadesFalso(RepositorioAmistades):
    def __init__(self, nombres=None):
        self.amistades = {}
        self.nombres = nombres or {}

    def buscar(self, amistad_id):
        return self.amistades.get(amistad_id)

    def buscar_entre(self, usuario_a, usuario_b):
        return next((a for a in self.amistades.values()
                     if {a.solicitante_id, a.destinatario_id} == {usuario_a, usuario_b}), None)

    def crear(self, solicitante_id, destinatario_id):
        if self.buscar_entre(solicitante_id, destinatario_id):
            raise SolicitudYaExiste()
        amistad = Amistad(len(self.amistades) + 1, solicitante_id, self.nombres.get(solicitante_id, ""),
                          destinatario_id, self.nombres.get(destinatario_id, ""), creada_en=AHORA)
        self.amistades[amistad.id] = amistad
        return amistad

    def aceptar(self, amistad_id, cuando):
        self.amistades[amistad_id].aceptada_en = cuando

    def eliminar(self, amistad_id):
        self.amistades.pop(amistad_id, None)

    def listar_de_usuario(self, usuario_id):
        return [a for a in self.amistades.values() if a.participa(usuario_id)]

    def ids_amigos(self, usuario_id):
        return {a.otro(usuario_id)[0] for a in self.listar_de_usuario(usuario_id) if a.aceptada}


@pytest.fixture
def entorno():
    usuarios = _RepositorioUsuariosFalso()
    ana = usuarios.crear("Ana", "ana@correo.com", "x")
    beto = usuarios.crear("Beto", "beto@correo.com", "x")
    caro = usuarios.crear("Caro", "caro@correo.com", "x")
    amistades = _RepositorioAmistadesFalso({u.id: u.nombre for u in (ana, beto, caro)})
    return usuarios, amistades, ana, beto, caro


def test_solicitar_crea_una_solicitud_pendiente(entorno):
    usuarios, amistades, ana, beto, _ = entorno

    amistad = SolicitarAmistad(amistades, usuarios).ejecutar(ana.id, " BETO@correo.com ", AHORA)

    assert not amistad.aceptada
    assert amistad.estado_para(ana.id) == "enviada"
    assert amistad.estado_para(beto.id) == "recibida"
    assert amistades.ids_amigos(ana.id) == set()


def test_al_aceptar_quedan_amigos_los_dos(entorno):
    usuarios, amistades, ana, beto, _ = entorno
    amistad = SolicitarAmistad(amistades, usuarios).ejecutar(ana.id, "beto@correo.com", AHORA)

    AceptarAmistad(amistades).ejecutar(beto.id, amistad.id, AHORA)

    assert amistades.ids_amigos(ana.id) == {beto.id}
    assert amistades.ids_amigos(beto.id) == {ana.id}


def test_solo_el_destinatario_puede_aceptar(entorno):
    usuarios, amistades, ana, _, caro = entorno
    amistad = SolicitarAmistad(amistades, usuarios).ejecutar(ana.id, "beto@correo.com", AHORA)

    for intruso in (ana.id, caro.id):
        with pytest.raises(AmistadNoEncontrada):
            AceptarAmistad(amistades).ejecutar(intruso, amistad.id, AHORA)
    assert not amistad.aceptada


def test_si_el_otro_ya_te_la_envio_enviarla_de_vuelta_la_acepta(entorno):
    usuarios, amistades, ana, beto, _ = entorno
    SolicitarAmistad(amistades, usuarios).ejecutar(ana.id, "beto@correo.com", AHORA)

    amistad = SolicitarAmistad(amistades, usuarios).ejecutar(beto.id, "ana@correo.com", AHORA)

    assert amistad.aceptada
    assert len(amistades.amistades) == 1


def test_no_se_repite_la_solicitud_ni_se_pide_dos_veces_a_un_amigo(entorno):
    usuarios, amistades, ana, beto, _ = entorno
    solicitar = SolicitarAmistad(amistades, usuarios)
    amistad = solicitar.ejecutar(ana.id, "beto@correo.com", AHORA)

    with pytest.raises(SolicitudYaExiste):
        solicitar.ejecutar(ana.id, "beto@correo.com", AHORA)

    AceptarAmistad(amistades).ejecutar(beto.id, amistad.id, AHORA)
    with pytest.raises(YaSonAmigos):
        solicitar.ejecutar(ana.id, "beto@correo.com", AHORA)


@pytest.mark.parametrize("correo, error", [
    ("nadie@correo.com", AmigoNoRegistrado),
    ("ana@correo.com", SolicitudInvalida),
])
def test_correo_desconocido_o_propio_se_rechaza(entorno, correo, error):
    usuarios, amistades, ana, _, _ = entorno

    with pytest.raises(error):
        SolicitarAmistad(amistades, usuarios).ejecutar(ana.id, correo, AHORA)


def test_cualquiera_de_los_dos_puede_borrarla_pero_no_un_tercero(entorno):
    usuarios, amistades, ana, beto, caro = entorno
    amistad = SolicitarAmistad(amistades, usuarios).ejecutar(ana.id, "beto@correo.com", AHORA)

    with pytest.raises(AmistadNoEncontrada):
        EliminarAmistad(amistades).ejecutar(caro.id, amistad.id)

    EliminarAmistad(amistades).ejecutar(beto.id, amistad.id)
    assert ListarAmistades(amistades).ejecutar(ana.id) == []


# ------------------------------------------------------------------ API

@pytest.fixture
def api(entorno):
    usuarios, amistades, ana, beto, caro = entorno
    tokens = TokensJwt("s" * 40)
    app = Flask(__name__)
    app.register_blueprint(crear_api_amigos(
        ListarAmistades(amistades), SolicitarAmistad(amistades, usuarios),
        AceptarAmistad(amistades), EliminarAmistad(amistades), crear_requiere_usuario(tokens),
    ))
    cabecera = {u.nombre: {"Authorization": f"Bearer {tokens.emitir_para_usuario(u.id)}"} for u in (ana, beto, caro)}
    return app.test_client(), cabecera


def test_api_flujo_completo_de_amistad(api):
    client, cabecera = api

    creada = client.post("/api/amigos", json={"correo": "beto@correo.com"}, headers=cabecera["Ana"])
    assert creada.status_code == 201
    assert creada.get_json()["estado"] == "enviada"
    assert creada.get_json()["usuario"] == {"id": 2, "nombre": "Beto"}

    pendientes = client.get("/api/amigos", headers=cabecera["Beto"]).get_json()
    assert [(a["usuario"]["nombre"], a["estado"]) for a in pendientes] == [("Ana", "recibida")]

    aceptada = client.post(f"/api/amigos/{pendientes[0]['id']}/aceptar", headers=cabecera["Beto"])
    assert aceptada.status_code == 200
    assert aceptada.get_json()["estado"] == "amigos"

    borrada = client.delete(f"/api/amigos/{pendientes[0]['id']}", headers=cabecera["Ana"])
    assert borrada.status_code == 204
    assert client.get("/api/amigos", headers=cabecera["Ana"]).get_json() == []


def test_api_errores_de_amistad(api):
    client, cabecera = api

    assert client.post("/api/amigos", json={}, headers=cabecera["Ana"]).status_code == 400
    assert client.post("/api/amigos", json={"correo": "ana@correo.com"}, headers=cabecera["Ana"]).status_code == 400
    assert client.post("/api/amigos", json={"correo": "x@correo.com"}, headers=cabecera["Ana"]).status_code == 404
    client.post("/api/amigos", json={"correo": "beto@correo.com"}, headers=cabecera["Ana"])
    repetida = client.post("/api/amigos", json={"correo": "beto@correo.com"}, headers=cabecera["Ana"])
    assert repetida.status_code == 409
    assert repetida.get_json()["error"] == "SOLICITUD_YA_ENVIADA"
    assert client.post("/api/amigos/1/aceptar", headers=cabecera["Caro"]).status_code == 404
    assert client.get("/api/amigos").status_code == 401


def test_api_solicitud_cruzada_devuelve_200_y_quedan_amigos(api):
    client, cabecera = api
    client.post("/api/amigos", json={"correo": "beto@correo.com"}, headers=cabecera["Ana"])

    respuesta = client.post("/api/amigos", json={"correo": "ana@correo.com"}, headers=cabecera["Beto"])

    assert respuesta.status_code == 200
    assert respuesta.get_json()["estado"] == "amigos"
