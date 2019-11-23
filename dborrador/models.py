from django.db import models
from django.contrib.postgres.fields import IntegerRangeField

from collections import namedtuple

from encuestas.models import PreferenciasDocente
from materias.models import Turno, Carga, choice_enum, TipoDocentes, Cuatrimestres


class Intento(namedtuple('Intento', ['algoritmo', 'manual'])):
    '''Modela una tupla de dos enteros entre 0 y (2 ** 16 - 1)'''

    @property
    def valor(self):
        return self.algoritmo * 2 ** 16 + self.manual

    @classmethod
    def de_valor(cls, valor):
        algoritmo = valor // (2 ** 16)
        manual = valor % (2 ** 16)
        return cls(algoritmo, manual)

    @classmethod
    def de_algoritmo(cls, algoritmo):
        return cls(algoritmo, 0)

    @classmethod
    def es_de_algoritmo(cls, valor):
        i = cls.de_valor(valor)
        return i.manual == 0



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
    def validas_en(cls, anno, cuatrimestre, intento):
        return cls.objects.filter(carga__anno=anno, carga__cuatrimestre=cuatrimestre, intentos__contains=intento.valor)

    @property
    def es_manual(self):
        return not Intento.es_de_algoritmo(self.intentos.lower)

    class Meta:
        verbose_name = 'asignación'
        verbose_name_plural = 'asignaciones'


class IntentoRegistrado(models.Model):
    '''Un modelo para llevar registro de los intentos de distribución'''

    intento = models.IntegerField()
    anno = models.IntegerField()
    cuatrimestre = models.CharField(max_length=1, choices=choice_enum(Cuatrimestres))
    fecha = models.DateTimeField(auto_now=True)

    @classmethod
    def maximo_intento(cls, anno, cuatrimestre):
        valor = 0
        intentos = cls.objects.filter(anno=anno, cuatrimestre=cuatrimestre)
        if intentos.count() > 0:
            valor = intentos.aggregate(models.Max('intento'))['intento__max']

        return Intento.de_valor(valor)
