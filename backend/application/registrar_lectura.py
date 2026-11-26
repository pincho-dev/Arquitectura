from domain.plantas import ORIGEN_DISPOSITIVO, ORIGEN_FORMULARIO, Lectura, MateraSinDueno, PlantaNoEncontrada
from application.avisos import AvisarDuenosNulo
from domain.puertos_entrada import RegistrarLecturaPort


class RegistrarLectura(RegistrarLecturaPort):
    """Mismo caso de uso para el formulario del front y para el ESP32: lo único
    que cambia es cómo se autorizó quien reporta."""

    def __init__(self, repositorio_plantas, historial, diagnosticar, avisos=None):
        self.repositorio_plantas = repositorio_plantas
        self.historial = historial
        self.diagnosticar = diagnosticar
        # Tiempo real: cada lectura guardada se avisa a los dueños de la planta,
        # sin importar por qué adaptador llegó (formulario, HTTP o WebSocket).
        self.avisos = avisos or AvisarDuenosNulo()

    def desde_formulario(self, usuario_id, planta_id, humedad, luz, temperatura, medida_en):
        planta = self._buscar_planta(planta_id)
        planta.verificar_acceso(usuario_id)
        return self._registrar(planta, humedad, luz, temperatura, medida_en, ORIGEN_FORMULARIO, None, None)

    def desde_dispositivo(self, dispositivo, humedad, luz, temperatura, medida_en):
        # La planta sale del dispositivo autenticado, nunca de la petición:
        # así un dispositivo no puede reportar para otra planta.
        if not dispositivo.tiene_dueno():
            raise MateraSinDueno(f"La matera {dispositivo.codigo} todavía no fue reclamada por ningún usuario.")
        planta = self._buscar_planta(dispositivo.planta_id)
        return self._registrar(planta, humedad, luz, temperatura, medida_en, ORIGEN_DISPOSITIVO,
                               dispositivo.id, dispositivo.codigo)

    def _buscar_planta(self, planta_id):
        planta = self.repositorio_plantas.buscar(planta_id)
        if planta is None:
            raise PlantaNoEncontrada(f"La planta {planta_id} no existe.")
        return planta

    def _registrar(self, planta, humedad, luz, temperatura, medida_en, origen, dispositivo_id, codigo):
        # Reutiliza la validación de la fase 1: si la lectura es físicamente
        # imposible, lanza ValorFueraDeRangoFisico y no se guarda nada.
        diagnostico = self.diagnosticar.ejecutar(planta.especie, humedad, luz, temperatura)
        lectura = Lectura(
            planta_id = planta.id,
            humedad = humedad,
            luz = luz,
            temperatura = temperatura,
            estado = diagnostico.estado,
            medida_en = medida_en,
            origen = origen,
            dispositivo_id = dispositivo_id
        )
        self.historial.guardar(lectura)
        self.avisos.lectura(lectura, codigo)
        return diagnostico
