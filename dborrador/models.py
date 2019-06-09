from django.db import models
from django.contrib.postgres.fields import IntegerRangeField

from collections import namedtuple

from encuestas.models import PreferenciasDocente
from materias.models import Turno, Carga, choice_enum, TipoDocentes


class Intento(namedtuple('Intento', ['algoritmo', 'manual'])):
    '''Modela una tupla de dos enteros entre 0 y (2 ** 16 - 1)'''

    @property
    def value(self):
        return self.algoritmo * 2 ** 16 + self.manual

    @classmethod
    def from_value(cls, value):
        algoritmo = value // (2 ** 16)
        manual = value % (2 ** 16)
        return cls(algoritmo, manual)



class Preferencia(models.Model):
    preferencia = models.ForeignKey(PreferenciasDocente, on_delete=models.CASCADE)
    peso_normalizado = models.FloatField()

    def __str__(self):
        return f'{self.preferencia.docente} -- {self.peso_normalizado:.4f} -> {self.preferencia.turno}'


class Asignacion(models.Model):
    intentos = IntegerRangeField()
    carga = models.ForeignKey(Carga, on_delete=models.CASCADE)
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE)
    cargo_que_ocupa = models.CharField(max_length=2, choices=choice_enum(TipoDocentes))

    def __str__(self):
        return f'{self.carga.docente} -> {self.turno}'

    @classmethod
    def validas_en(cls, intento):
        return cls.objects.filter(intentos__contains=intento.value)

    class Meta:
        verbose_name = 'asignación'
        verbose_name_plural = 'asignaciones'


class Comentario(models.Model):
    texto = models.TextField()
    intento = models.IntegerField()
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE)
