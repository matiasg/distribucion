from django.db import models

from encuestas.models import PreferenciasDocente
from materias.models import Docente, Turno


class Preferencia(models.Model):
    preferencia = models.ForeignKey(PreferenciasDocente, on_delete=models.CASCADE)


class Asignacion(models.Model):
    intento = models.IntegerField()
    docente = models.ForeignKey(Docente, on_delete=models.CASCADE)
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE)

