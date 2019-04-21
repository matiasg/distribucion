from django.db import models
from simple_history.models import HistoricalRecords

from materias.models import Turno, Docente, Cuatrimestres, Cargos, choice_enum

class PreferenciasDocente(models.Model):
    docente = models.ForeignKey(Docente, on_delete=models.CASCADE)
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE)
    cargo = models.CharField(max_length=3, choices=choice_enum(Cargos))
    peso = models.FloatField(null=True)
    fecha_encuesta = models.DateTimeField()
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.docente} -- {self.peso} -> {self.turno}'
