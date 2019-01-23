from django.db import models

from materias.models import Turno, Docente

class PreferenciasDocente(models.Model):
    docente = models.ForeignKey(Docente, on_delete=models.CASCADE)
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE)
    peso = models.FloatField(null=True)

