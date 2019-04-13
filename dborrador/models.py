from django.db import models

from encuestas.models import PreferenciasDocente
from materias.models import Turno, Carga


class Preferencia(models.Model):
    preferencia = models.ForeignKey(PreferenciasDocente, on_delete=models.CASCADE)
    peso_normalizado = models.FloatField()

    def __str__(self):
        return f'{self.preferencia.docente} -- {self.peso_normalizado:.4f} -> {self.preferencia.turno}'


class Asignacion(models.Model):
    intento = models.IntegerField()
    carga = models.ForeignKey(Carga, on_delete=models.CASCADE)
    # docente = models.ForeignKey(Docente, on_delete=models.CASCADE)
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE)

    def __str__(self):
        return f'Intento {self.intento}: {self.carga.docente} -> {self.turno} '

    class Meta:
        verbose_name = 'asignación'
        verbose_name_plural = 'asignaciones'
