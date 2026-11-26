"""WebSockets de los ESP32 (/ws/dispositivos) y del front (/ws/app) contra un
servidor real en un hilo, con dobles de prueba en vez de la BD."""
import json
import threading
import time

import pytest
import websocket
from flask import Flask
from flask_sock import Sock
from werkzeug.serving import make_server

from application.avisos import AvisarDuenos
from application.diagnosticar_planta import DiagnosticarPlanta
from application.consultar_plantas import ListarPlantas
from application.enviar_orden import EnviarOrden
from application.registrar_lectura import RegistrarLectura
from domain.ordenes import DispositivoDesconectado, Orden, OrdenInvalida
from domain.plantas import AccesoDenegado, Dispositivo
from infrastructure.canal_websocket import CanalAppWebSocket, CanalDispositivosWebSocket
from infrastructure.tokens_jwt import TokensJwt
from presentation.ws_app import registrar_websocket_app
from presentation.ws_dispositivos import registrar_websocket_dispositivos
from tests.test_plantas import (
    AJENO, DUENA, _EspecieLookupFalso, _HistorialFalso, _RepositorioDispositivosFalso, _RepositorioPlantasFalso,
)

TOKEN = "dev_token_valido"
SECRETO = "s" * 40


class _AutenticadorFalso:
    """Como AutenticadorDispositivosBd: cada llamada devuelve el estado actual
    de la matera (puede haber sido reclamada o revocada mientras tanto)."""

    def __init__(self, codigo, planta_id):
        self.codigo, self.planta_id, self.revocado = codigo, planta_id, False

    def autenticar(self, token):
        if token != TOKEN or self.revocado:
            return None
        return Dispositivo(9, self.codigo, self.planta_id)


class _Entorno:
    def __init__(self, ping_s=None, planta_reclamada=True):
        self.plantas, self.historial = _RepositorioPlantasFalso(), _HistorialFalso()
        self.dispositivos = _RepositorioDispositivosFalso()
        self.planta = self.plantas.crear("Potos sala", "potos", DUENA)
        diagnosticar = DiagnosticarPlanta(_EspecieLookupFalso())
        self.canal, self.canal_app = CanalDispositivosWebSocket(), CanalAppWebSocket()
        avisos = AvisarDuenos(self.plantas, self.canal_app)
        registrar = RegistrarLectura(self.plantas, self.historial, diagnosticar, avisos)
        self.autenticador = _AutenticadorFalso("MAT-TEST", self.planta.id if planta_reclamada else None)
        # La matera también existe en el repositorio (para ListarPlantas y EnviarOrden).
        self.dispositivos.registrar("MAT-TEST", self.planta.id, TOKEN)
        self.tokens = TokensJwt(SECRETO)

        app = Flask(__name__)
        if ping_s:
            app.config["SOCK_SERVER_OPTIONS"] = {"ping_interval": ping_s}
        sock = Sock(app)
        registrar_websocket_dispositivos(sock, self.autenticador, registrar, self.canal, avisos, intervalo_s=10)
        listar = ListarPlantas(self.plantas, self.historial, self.dispositivos, diagnosticar)
        registrar_websocket_app(sock, self.canal_app, self.tokens, listar, self.canal)
        self.enviar_orden = EnviarOrden(self.dispositivos, self.plantas, self.canal)

        self.servidor = make_server("127.0.0.1", 0, app, threaded=True)
        self.url = f"ws://127.0.0.1:{self.servidor.server_port}"
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()

    def esp(self, token=TOKEN, codigo="MAT-TEST"):
        ws = websocket.create_connection(f"{self.url}/ws/dispositivos", timeout=5)
        enviar(ws, tipo="hola", codigo=codigo, token=token, firmware="test")
        return ws

    def app(self, usuario_id):
        ws = websocket.create_connection(f"{self.url}/ws/app", timeout=5)
        enviar(ws, tipo="auth", token=self.tokens.emitir_para_usuario(usuario_id))
        estado = recibir(ws)
        assert estado["tipo"] == "estado"
        return ws, estado

    def cerrar(self):
        self.servidor.shutdown()


def enviar(ws, **mensaje):
    ws.send(json.dumps(mensaje))


def recibir(ws):
    return json.loads(ws.recv())


def esperar(condicion, segundos=3):
    limite = time.time() + segundos
    while time.time() < limite:
        if condicion():
            return True
        time.sleep(0.05)
    return False


@pytest.fixture
def entorno():
    e = _Entorno()
    yield e
    e.cerrar()


# ------------------------------------------------------------ ESP32 -> backend

def codigo_de_cierre(ws):
    opcode, datos = ws.recv_data(control_frame=True)
    assert opcode == websocket.ABNF.OPCODE_CLOSE
    return int.from_bytes(datos[:2], "big")


def test_esp_con_token_invalido_es_rechazada(entorno):
    ws = entorno.esp(token="dev_falso")
    assert recibir(ws)["error"] == "NO_AUTORIZADO"
    assert codigo_de_cierre(ws) == 4401
    assert entorno.canal.presencia("MAT-TEST") == (False, None)


def test_esp_no_puede_suplantar_otro_codigo(entorno):
    ws = entorno.esp(codigo="MAT-OTRA")
    assert recibir(ws)["error"] == "ACCESO_DENEGADO"


def test_esp_sin_saludo_es_rechazada(entorno):
    ws = websocket.create_connection(f"{entorno.url}/ws/dispositivos", timeout=5)
    enviar(ws, tipo="lectura", humedad=50, luz=500, temperatura=22)
    assert recibir(ws)["error"] == "SALUDO_REQUERIDO"


def test_lectura_por_websocket_se_guarda_y_se_diagnostica(entorno):
    ws = entorno.esp()
    bienvenida = recibir(ws)
    assert bienvenida == {"tipo": "bienvenida", "codigo": "MAT-TEST", "reclamada": True, "intervalo_s": 10}
    assert entorno.canal.presencia("MAT-TEST")[0] is True

    enviar(ws, tipo="lectura", humedad=55, luz=700, temperatura=24)
    respuesta = recibir(ws)
    assert respuesta["tipo"] == "lectura_ok" and respuesta["estado"] == "SALUDABLE"
    assert len(entorno.historial.lecturas) == 1
    assert entorno.historial.lecturas[0].origen == "dispositivo"


def test_lectura_invalida_no_tumba_la_conexion(entorno):
    ws = entorno.esp()
    recibir(ws)
    enviar(ws, tipo="lectura", humedad="sensor-error", luz=700, temperatura=24)
    assert recibir(ws)["error"] == "PARAMETRO_INVALIDO"
    enviar(ws, tipo="lectura", humedad=140, luz=700, temperatura=24)
    assert recibir(ws)["error"] == "PARAMETRO_INVALIDO"
    ws.send("esto no es json")
    assert recibir(ws)["error"] == "MENSAJE_INVALIDO"
    enviar(ws, tipo="lectura", humedad=55, luz=700, temperatura=24)
    assert recibir(ws)["tipo"] == "lectura_ok"
    assert len(entorno.historial.lecturas) == 1


def test_matera_reclamada_con_el_esp_conectado_empieza_a_reportar_sin_reconectarse():
    e = _Entorno(planta_reclamada=False)
    try:
        ws = e.esp()
        assert recibir(ws)["reclamada"] is False
        enviar(ws, tipo="lectura", humedad=55, luz=700, temperatura=24)
        assert recibir(ws)["error"] == "MATERA_SIN_DUENO"

        e.autenticador.planta_id = e.planta.id     # alguien tocó el sticker
        app, _ = e.app(DUENA)
        enviar(ws, tipo="lectura", humedad=55, luz=700, temperatura=24)
        assert recibir(ws)["tipo"] == "lectura_ok"
        assert recibir(app)["tipo"] == "conexion"      # la dueña nueva ve que está conectada
        assert recibir(app)["tipo"] == "lectura"
    finally:
        e.cerrar()


def test_matera_revocada_se_corta_en_la_siguiente_lectura(entorno):
    ws = entorno.esp()
    recibir(ws)
    entorno.autenticador.revocado = True
    enviar(ws, tipo="lectura", humedad=55, luz=700, temperatura=24)
    assert recibir(ws)["error"] == "NO_AUTORIZADO"
    assert esperar(lambda: entorno.canal.presencia("MAT-TEST")[0] is False)


# ------------------------------------------------------------ backend -> front

def test_app_sin_jwt_valido_es_rechazada(entorno):
    ws = websocket.create_connection(f"{entorno.url}/ws/app", timeout=5)
    enviar(ws, tipo="auth", token="no-es-un-jwt")
    assert recibir(ws)["error"] == "NO_AUTENTICADO"
    assert codigo_de_cierre(ws) == 4401


def test_la_duena_ve_en_vivo_conexion_lectura_y_desconexion(entorno):
    app, estado = entorno.app(DUENA)
    assert estado["dispositivos"][0]["codigo"] == "MAT-TEST"
    assert estado["dispositivos"][0]["conectado"] is False

    ws = entorno.esp()
    recibir(ws)
    aviso = recibir(app)
    assert aviso == {"tipo": "conexion", "planta_id": entorno.planta.id, "codigo": "MAT-TEST", "conectado": True}

    enviar(ws, tipo="lectura", humedad=10, luz=700, temperatura=24)
    recibir(ws)
    aviso = recibir(app)
    assert aviso["tipo"] == "lectura" and aviso["codigo"] == "MAT-TEST"
    assert aviso["lectura"]["humedad"] == 10 and aviso["lectura"]["estado"] == "CRITICO"

    ws.close()
    aviso = recibir(app)
    assert aviso["tipo"] == "conexion" and aviso["conectado"] is False


def test_un_usuario_ajeno_no_recibe_avisos_de_plantas_que_no_son_suyas(entorno):
    ajeno, estado = entorno.app(AJENO)
    assert estado["dispositivos"] == []
    ws = entorno.esp()
    recibir(ws)
    enviar(ws, tipo="lectura", humedad=55, luz=700, temperatura=24)
    recibir(ws)
    ajeno.settimeout(0.5)
    with pytest.raises(websocket.WebSocketTimeoutException):
        ajeno.recv()


def test_co_duenos_reciben_los_avisos_de_la_planta_compartida(entorno):
    entorno.plantas.agregar_dueno(entorno.planta.id, AJENO)
    invitado, _ = entorno.app(AJENO)
    entorno.esp()
    assert recibir(invitado)["tipo"] == "conexion"


# ------------------------------------------------------------ heartbeat

def test_esp_desenchufada_de_golpe_se_detecta_por_el_ping():
    # Un cliente que deja de leer no responde los ping: es lo que pasa cuando
    # al ESP32 le quitan la corriente y nunca alcanza a cerrar el socket.
    e = _Entorno(ping_s=0.5)
    try:
        app, _ = e.app(DUENA)
        ws = e.esp()
        recibir(ws)
        assert recibir(app)["conectado"] is True
        # El front sí responde los ping porque sigue leyendo; la ESP "muerta" no.
        aviso = recibir(app)
        assert aviso["tipo"] == "conexion" and aviso["conectado"] is False
        assert e.canal.presencia("MAT-TEST")[0] is False
    finally:
        e.cerrar()


def test_reconexion_no_genera_un_falso_desconectado(entorno):
    app, _ = entorno.app(DUENA)
    vieja = entorno.esp()
    recibir(vieja)
    assert recibir(app)["conectado"] is True
    nueva = entorno.esp()
    recibir(nueva)
    assert recibir(app)["conectado"] is True
    app.settimeout(0.5)
    with pytest.raises(websocket.WebSocketTimeoutException):
        app.recv()   # el cierre del socket viejo no se avisa como desconexión
    assert entorno.canal.presencia("MAT-TEST")[0] is True


# ------------------------------------------------------------ órdenes

def test_orden_llega_al_esp_y_su_confirmacion_a_la_app(entorno):
    app, _ = entorno.app(DUENA)
    ws = entorno.esp()
    recibir(ws)
    recibir(app)

    id_orden = entorno.enviar_orden.ejecutar(DUENA, "mat-test", "regar", {"segundos": 5})
    orden = recibir(ws)
    assert orden == {"tipo": "orden", "id": id_orden, "orden": "regar", "parametros": {"segundos": 5}}

    enviar(ws, tipo="orden_ok", id=id_orden)
    assert recibir(app) == {"tipo": "orden_ok", "planta_id": entorno.planta.id, "codigo": "MAT-TEST", "id": id_orden}


def test_no_se_puede_ordenar_a_una_matera_ajena_o_desconectada(entorno):
    with pytest.raises(DispositivoDesconectado):
        entorno.enviar_orden.ejecutar(DUENA, "MAT-TEST", "parpadear")
    with pytest.raises(AccesoDenegado):
        entorno.enviar_orden.ejecutar(AJENO, "MAT-TEST", "parpadear")


@pytest.mark.parametrize("nombre, parametros", [
    ("explotar", None), ("regar", None), ("regar", {"segundos": 99}),
    ("regar", {"segundos": True}), ("parpadear", {"veces": 3}), ("parpadear", []),
])
def test_ordenes_invalidas(nombre, parametros):
    with pytest.raises(OrdenInvalida):
        Orden(nombre, parametros)
