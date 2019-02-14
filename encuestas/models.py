from django.db import models

from materias.models import Turno, Docente, Cuatrimestres, choice_enum

class PreferenciasDocente(models.Model):
    docente = models.ForeignKey(Docente, on_delete=models.CASCADE)
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE)
    peso = models.FloatField(null=True)
    anno = models.IntegerField()
    cuatrimestre = models.CharField(max_length=1, choices=choice_enum(Cuatrimestres))
    fecha_encuesta = models.DateTimeField()

