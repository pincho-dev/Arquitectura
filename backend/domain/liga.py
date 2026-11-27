"""
Reglas de la liga (gamificación). Dominio puro: sin BD, sin HTTP y sin reloj
(el "ahora" y la zona horaria llegan como parámetros).

Cómo se ganan los puntos (decidido en la sesión 2026-11-26, ver la bitácora):

- Solo cuentan las lecturas de las materas (origen dispositivo): las del
  formulario se pueden inventar.
- Cada lectura "vale" hasta la siguiente, pero como mucho HUECO_MAXIMO. Si la
  matera dejó de reportar más tiempo, ese rato cuenta como desconectada:
  desenchufarla no da puntos ni los quita.
- Puntos de un día (0–100) = PESO_CALIDAD × calidad + PESO_REACCION × reacción.
  · calidad: fracción del tiempo conectada en que estuvo saludable (en riesgo
    vale la mitad, crítico cero).
  · reacción: por cada episodio (pasar de saludable a en riesgo o crítico),
    qué tan rápido volvió a saludable; tardar REACCION_MAXIMA o más vale cero.
    Sin episodios ese día, reacción completa.
- Un día cuenta si la planta estuvo conectada al menos MINIMO_CONECTADA_DIA.
- La planta clasifica en el mes si estuvo conectada MINIMO_CONECTADA_MES en
  total. Sus puntos del mes son el promedio de sus días válidos.
- Los puntos del usuario son el promedio de sus plantas que clasifican: una
  planta descuidada baja el promedio.
- La división sale de los puntos por umbrales fijos. Mientras el usuario no
  clasifica en el mes, arranca una división por debajo de la del mes anterior.
"""
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone

from domain.plantas import VENTANA_CONEXION

SALUDABLE, EN_RIESGO, CRITICO = "SALUDABLE", "EN_RIESGO", "CRITICO"
VALOR_ESTADO = {SALUDABLE: 1.0, EN_RIESGO: 0.5, CRITICO: 0.0}

HUECO_MAXIMO = VENTANA_CONEXION
PESO_CALIDAD = 70
PESO_REACCION = 30
REACCION_MAXIMA = timedelta(hours=6)
MINIMO_CONECTADA_DIA = timedelta(hours=1)
MINIMO_CONECTADA_MES = timedelta(hours=24)

ALCANCE_GLOBAL = "global"
ALCANCE_AMIGOS = "amigos"
ALCANCES = (ALCANCE_GLOBAL, ALCANCE_AMIGOS)


class PeriodoInvalido(Exception):
    pass


class AlcanceInvalido(Exception):
    pass


# ------------------------------------------------------------- divisiones

@dataclass(frozen=True)
class Division:
    clave: str
    nombre: str
    metal: str
    minimo: int
    maximo: int


DIVISIONES = (
    Division("semilla", "Semilla", "Bronce", 0, 39),
    Division("brote", "Brote", "Plata", 40, 59),
    Division("hoja", "Hoja", "Oro", 60, 74),
    Division("flor", "Flor", "Esmeralda", 75, 89),
    Division("arbol", "Árbol", "Cristal", 90, 100),
)


def division_para(puntos):
    elegida = DIVISIONES[0]
    for division in DIVISIONES:
        if puntos >= division.minimo:
            elegida = division
    return elegida


def division_de_arranque(division_anterior):
    """Al empezar el mes se baja una división, no se vuelve a cero."""
    if division_anterior is None:
        return DIVISIONES[0]
    return DIVISIONES[max(DIVISIONES.index(division_anterior) - 1, 0)]


def siguiente_division(division):
    indice = DIVISIONES.index(division)
    return DIVISIONES[indice + 1] if indice + 1 < len(DIVISIONES) else None


def puntos_para_subir(puntos, division):
    siguiente = siguiente_division(division)
    if siguiente is None or puntos is None:
        return None
    return round(max(siguiente.minimo - puntos, 0), 1)


# ---------------------------------------------------------------- periodos

def periodo_del_mes(anio, mes, zona):
    """[inicio, fin) del mes en la zona horaria del usuario, en UTC."""
    if not 1 <= mes <= 12:
        raise PeriodoInvalido("El mes debe estar entre 1 y 12.")
    siguiente = (anio + 1, 1) if mes == 12 else (anio, mes + 1)
    inicio = datetime(anio, mes, 1, tzinfo=zona)
    fin = datetime(siguiente[0], siguiente[1], 1, tzinfo=zona)
    return inicio.astimezone(timezone.utc), fin.astimezone(timezone.utc)


def mes_anterior(anio, mes):
    return (anio - 1, 12) if mes == 1 else (anio, mes - 1)


# ------------------------------------------------------------- resultados

@dataclass(frozen=True)
class Participante:
    usuario_id: int
    nombre: str
    plantas: tuple = ()  # ((planta_id, nombre), ...)


@dataclass
class ResultadoPlanta:
    planta_id: int
    nombre: str
    puntos: float | None
    clasifica: bool
    conectada: timedelta
    dias_validos: int
    episodios: int


@dataclass
class ResultadoUsuario:
    usuario_id: int
    nombre: str
    plantas: list = field(default_factory=list)

    @property
    def clasifica(self):
        return any(p.clasifica for p in self.plantas)

    @property
    def puntos(self):
        """Promedio de las plantas que clasifican; None si ninguna clasifica."""
        return _promedio([p.puntos for p in self.plantas if p.clasifica])

    @property
    def puntos_provisionales(self):
        """Lo que lleva hasta ahora, aunque todavía no clasifique."""
        return _promedio([p.puntos for p in self.plantas if p.puntos is not None])


@dataclass
class FilaRanking:
    posicion: int
    resultado: ResultadoUsuario
    division: Division


def _promedio(valores):
    return round(sum(valores) / len(valores), 1) if valores else None


# --------------------------------------------------------------- cálculo

@dataclass
class _Dia:
    conectada: float = 0.0  # segundos
    valor: float = 0.0      # segundos ponderados por VALOR_ESTADO
    reacciones: list = field(default_factory=list)


def evaluar_planta(planta_id, nombre, estados, desde, hasta, zona):
    """estados: [(medida_en, estado)] de las lecturas de la matera.
    hasta ya viene recortado a "ahora" si el mes no ha terminado."""
    estados = sorted((t, e) for t, e in estados if desde <= t < hasta)
    dias = {}

    for i, (inicio, estado) in enumerate(estados):
        siguiente = estados[i + 1][0] if i + 1 < len(estados) else hasta
        fin = min(siguiente, inicio + HUECO_MAXIMO, hasta)
        _repartir_por_dia(inicio, fin, VALOR_ESTADO[estado], dias, zona)

    # Un episodio cuenta en cada día que dura: si sigue sin resolverse al día
    # siguiente, ese día tampoco tiene la reacción completa.
    episodios = _episodios(estados, hasta)
    for inicio, duracion in episodios:
        reaccion = max(0.0, 1 - duracion / REACCION_MAXIMA)
        fecha, ultima = inicio.astimezone(zona).date(), (inicio + duracion).astimezone(zona).date()
        while fecha <= ultima:
            if fecha in dias:
                dias[fecha].reacciones.append(reaccion)
            fecha += timedelta(days=1)

    puntos_dias = [
        PESO_CALIDAD * (d.valor / d.conectada)
        + PESO_REACCION * (sum(d.reacciones) / len(d.reacciones) if d.reacciones else 1.0)
        for d in dias.values()
        if d.conectada >= MINIMO_CONECTADA_DIA.total_seconds()
    ]
    conectada = timedelta(seconds=sum(d.conectada for d in dias.values()))
    return ResultadoPlanta(
        planta_id=planta_id,
        nombre=nombre,
        puntos=_promedio(puntos_dias),
        clasifica=bool(puntos_dias) and conectada >= MINIMO_CONECTADA_MES,
        conectada=conectada,
        dias_validos=len(puntos_dias),
        episodios=len(episodios),
    )


def _repartir_por_dia(inicio, fin, valor, dias, zona):
    """Suma el intervalo [inicio, fin) a cada día local que toca."""
    while inicio < fin:
        fecha = inicio.astimezone(zona).date()
        fin_del_dia = datetime.combine(fecha + timedelta(days=1), time(0), tzinfo=zona)
        tramo_fin = min(fin, fin_del_dia)
        segundos = (tramo_fin - inicio).total_seconds()
        dia = dias.setdefault(fecha, _Dia())
        dia.conectada += segundos
        dia.valor += segundos * valor
        inicio = tramo_fin


def _episodios(estados, hasta):
    """[(inicio, duración)] de cada vez que dejó de estar saludable. Si no se
    recuperó todavía, la duración va hasta `hasta`."""
    episodios, inicio = [], None
    for t, estado in estados:
        if estado != SALUDABLE and inicio is None:
            inicio = t
        elif estado == SALUDABLE and inicio is not None:
            episodios.append((inicio, t - inicio))
            inicio = None
    if inicio is not None:
        episodios.append((inicio, hasta - inicio))
    return episodios


def evaluar_usuario(participante, estados_por_planta, desde, hasta, zona):
    return ResultadoUsuario(
        usuario_id=participante.usuario_id,
        nombre=participante.nombre,
        plantas=[
            evaluar_planta(planta_id, nombre, estados_por_planta.get(planta_id, ()), desde, hasta, zona)
            for planta_id, nombre in participante.plantas
        ],
    )


def armar_ranking(resultados):
    """Solo entran los que clasifican. Empates: misma posición (1, 1, 3)."""
    clasificados = sorted(
        (r for r in resultados if r.clasifica),
        key=lambda r: (-r.puntos, r.nombre.lower(), r.usuario_id),
    )
    filas = []
    for i, resultado in enumerate(clasificados):
        if filas and resultado.puntos == filas[-1].resultado.puntos:
            posicion = filas[-1].posicion
        else:
            posicion = i + 1
        filas.append(FilaRanking(posicion, resultado, division_para(resultado.puntos)))
    return filas
