from domain.puertos_entrada import ListarEspeciesPort
class ListarEspecies(ListarEspeciesPort):

    def __init__(self, catalogo_especies):
        self.catalogo_especies = catalogo_especies

    def ejecutar(self):
        return self.catalogo_especies.listar()