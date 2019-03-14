from django.db import models

from encuestas.models import PreferenciasDocente
from materias.models import Docente, Turno


class Preferencia(models.Model):
    preferencia = models.ForeignKey(PreferenciasDocente, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.preferencia}'


class Asignacion(models.Model):
    intento = models.IntegerField()
    docente = models.ForeignKey(Docente, on_delete=models.CASCADE)
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE)

    def __str__(self):
        return f'Intento {self.intento}: {self.docente} -> {self.turno} '

    class Meta:
        verbose_name = 'asignación'
        verbose_name_plural = 'asignaciones'
