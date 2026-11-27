from dataclasses import dataclass

from domain.liga import (
    ALCANCE_AMIGOS, ALCANCES, AlcanceInvalido, PeriodoInvalido, Participante, ResultadoUsuario,
    armar_ranking, division_de_arranque, division_para, evaluar_usuario, mes_anterior,
    periodo_del_mes, puntos_para_subir, siguiente_division,
)
from domain.puertos_entrada import ConsultarMiLigaPort, ConsultarRankingPort


@dataclass
class MiLiga:
    mes: tuple  # (anio, mes)
    resultado: ResultadoUsuario
    division: object
    division_mes_anterior: object
    siguiente_division: object
    puntos_para_subir: float | None


@dataclass
class Ranking:
    mes: tuple
    alcance: str
    filas: list
    mi_posicion: int | None


def _resolver_mes(ahora, zona, anio, mes):
    if anio is None or mes is None:
        local = ahora.astimezone(zona)
        anio, mes = local.year, local.month
    desde, hasta = periodo_del_mes(anio, mes, zona)
    if desde > ahora:
        raise PeriodoInvalido("Ese mes todavía no empieza.")
    return (anio, mes), desde, min(hasta, ahora)


def _evaluar(datos_liga, participantes, desde, hasta, zona):
    planta_ids = [planta_id for p in participantes for planta_id, _ in p.plantas]
    estados = datos_liga.estados(planta_ids, desde, hasta) if planta_ids else {}
    return [evaluar_usuario(p, estados, desde, hasta, zona) for p in participantes]


class ConsultarMiLiga(ConsultarMiLigaPort):

    def __init__(self, datos_liga, zona):
        self.datos_liga = datos_liga
        self.zona = zona

    def ejecutar(self, usuario_id, ahora, anio=None, mes=None):
        periodo, desde, hasta = _resolver_mes(ahora, self.zona, anio, mes)
        participantes = self.datos_liga.participantes([usuario_id]) or [Participante(usuario_id, "")]
        resultado = _evaluar(self.datos_liga, participantes, desde, hasta, self.zona)[0]

        # La división del mes anterior se calcula solo por sus puntos (si no
        # clasificó, queda sin división): no se encadenan meses hacia atrás.
        desde_ant, hasta_ant = periodo_del_mes(*mes_anterior(*periodo), self.zona)
        anterior = _evaluar(self.datos_liga, participantes, desde_ant, min(hasta_ant, ahora), self.zona)[0]
        division_anterior = division_para(anterior.puntos) if anterior.clasifica else None

        if resultado.clasifica:
            division = division_para(resultado.puntos)
            puntos = resultado.puntos
        else:
            division = division_de_arranque(division_anterior)
            puntos = resultado.puntos_provisionales
        return MiLiga(
            mes=periodo,
            resultado=resultado,
            division=division,
            division_mes_anterior=division_anterior,
            siguiente_division=siguiente_division(division),
            puntos_para_subir=puntos_para_subir(puntos, division),
        )


class ConsultarRanking(ConsultarRankingPort):

    def __init__(self, datos_liga, repositorio_amistades, zona):
        self.datos_liga = datos_liga
        self.repositorio_amistades = repositorio_amistades
        self.zona = zona

    def ejecutar(self, usuario_id, alcance, ahora, anio=None, mes=None):
        if alcance not in ALCANCES:
            raise AlcanceInvalido(f"El alcance debe ser uno de: {', '.join(ALCANCES)}.")
        periodo, desde, hasta = _resolver_mes(ahora, self.zona, anio, mes)

        if alcance == ALCANCE_AMIGOS:
            ids = self.repositorio_amistades.ids_amigos(usuario_id) | {usuario_id}
            participantes = self.datos_liga.participantes(sorted(ids))
        else:
            participantes = self.datos_liga.participantes()

        filas = armar_ranking(_evaluar(self.datos_liga, participantes, desde, hasta, self.zona))
        mi_posicion = next((f.posicion for f in filas if f.resultado.usuario_id == usuario_id), None)
        return Ranking(periodo, alcance, filas, mi_posicion)
