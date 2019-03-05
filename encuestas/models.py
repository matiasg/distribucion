from django.db import models

from materias.models import Turno, Docente, Cuatrimestres, choice_enum

class PreferenciasDocente(models.Model):
    docente = models.ForeignKey(Docente, on_delete=models.CASCADE)
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE)
    peso = models.FloatField(null=True)
    fecha_encuesta = models.DateTimeField()
