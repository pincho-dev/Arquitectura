from sqlalchemy import func, update

from domain.plantas import Dispositivo
from infrastructure.db.tablas import dispositivos
from infrastructure.tokens_dispositivo import hash_token_dispositivo


class AutenticadorDispositivosBd:
    """Verifica el token opaco de un dispositivo contra su hash en la BD.

    Lo usa solo el adaptador de entrada de dispositivos, igual que TokensJwt
    lo usa el del front: la verificación vive afuera del dominio.
    """

    def __init__(self, engine):
        self.engine = engine

    def autenticar(self, token):
        """Devuelve el Dispositivo dueño del token (si no está revocado) y
        registra su última conexión; None si el token no es válido."""
        with self.engine.begin() as conexion:
            fila = conexion.execute(
                update(dispositivos)
                .where(dispositivos.c.token_hash == hash_token_dispositivo(token),
                       dispositivos.c.revocado_en.is_(None))
                .values(ultima_conexion=func.now())
                .returning(dispositivos.c.id, dispositivos.c.codigo,
                           dispositivos.c.planta_id, dispositivos.c.ultima_conexion)
            ).first()
        if fila is None:
            return None
        return Dispositivo(fila.id, fila.codigo, fila.planta_id, fila.ultima_conexion)
