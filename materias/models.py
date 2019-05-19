from collections import namedtuple
from functools import total_ordering

from django.db import models
from django.core.validators import int_list_validator, MaxValueValidator
from django.contrib.postgres.fields import ArrayField
from simple_history.models import HistoricalRecords
from enum import Enum


@total_ordering
class Dias(Enum):
    Lu = ('Lunes', 1)
    Ma = ('Martes', 2)
    Mi = ('Miércoles', 3)
    Ju = ('Jueves', 4)
    Vi = ('Viernes', 5)

    def __lt__(self, other):
        return self.value[1] < other.value[1] if other.__class__ is Dias else NotImplemented


class Cargos(Enum):
    Tit = 'Prof. Titular'
    Aso = 'Prof. Asociado'
    Adj = 'Prof. Adjunto'
    JTP = 'Jefe de Trabajos Prácticos'
    Ay1 = 'Ayudante de 1ra'
    Ay2 = 'Ayudante de 2da'


class Dedicaciones(Enum) :
    Exc = 'Exclusiva'
    Smx = 'Semiexclusiva'
    Sim = 'Simple'


class CargoDedicacion(Enum):
    _ignore_ = 'cargo dedicacion CargoDedicacion'
    CargoDedicacion = vars()
    for cargo in Cargos:
        for dedicacion in Dedicaciones:
            CargoDedicacion[f'{cargo.name}{dedicacion.name}'] = f'{cargo.value} {dedicacion.value}'

    @classmethod
    def con_cargo(cls, cargo):
        '''Devuelve una lista de CargoDedicacion cuyo cargo es el parámetro :cargo:'''
        return [f'{cargo.name}{ded.name}' for ded in Dedicaciones]


class TipoTurno(Enum):
    T = 'Teórica'
    P = 'Práctica'
    A = 'Teórico-Práctica'


class Cuatrimestres(Enum):
    P = '1'
    S = '2'
    V = 'V'


class TipoMateria(Enum):
    B = 'obligatoria'
    R = 'optativa regular'
    N = 'optativa no regular'


def choice_enum(enum_cls, long_value=(lambda v: v)):
    return ((e.name, long_value(e.value)) for e in enum_cls)


def get_key_enum(enum_cls):
    return {e.value: e.name for e in enum_cls}


TurnoInfo = namedtuple('TurnoInfo', ['tipoynumero', 'diayhora', 'aula'])


class Materia(models.Model):
    nombre = models.CharField(max_length=120)
    obligatoriedad = models.CharField(max_length=1, choices=choice_enum(TipoMateria))
    history = HistoricalRecords()

    def __str__(self):
        return self.nombre


class Turno(models.Model):
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    anno = models.IntegerField()
    cuatrimestre = models.CharField(max_length=1, choices=choice_enum(Cuatrimestres))
    numero = models.IntegerField()
    subnumero = models.CharField(max_length=6, blank=True)
    tipo = models.CharField(max_length=1, choices=choice_enum(TipoTurno))
    necesidad_prof = models.PositiveIntegerField(validators=[MaxValueValidator(15)])
    necesidad_jtp = models.PositiveIntegerField(validators=[MaxValueValidator(15)])
    necesidad_ay1 = models.PositiveIntegerField(validators=[MaxValueValidator(15)])
    necesidad_ay2 = models.PositiveIntegerField(validators=[MaxValueValidator(15)])
    alumnos = models.PositiveIntegerField(validators=[MaxValueValidator(1000)], default=0)
    dificil_de_cubrir = models.BooleanField(default=False)
    history = HistoricalRecords()

    def __str__(self):
        numero = f' {self.numero}' if self.numero else ''
        return (f'{self.materia.nombre}, cuat {Cuatrimestres[self.cuatrimestre].value} {self.anno}, '
                f'{TipoTurno[self.tipo].value}{numero}')

    def horarios_info(self):

        def time_str(hms):
            if hms.minute:
                return f'{hms.hour}:{hms.minute:02d}'
            return f'{hms.hour}'

        def join(lst):
            if len(set(lst)) == 1:
                return lst[0]
            return ' y '.join(lst)

        tipo = f'{TipoTurno[self.tipo].value}'
        tipoynumero = f'{tipo} {self.numero}' if self.numero else tipo
        horarios = sorted(self.horario_set.all())
        dias = join([h.dia for h in horarios])
        horas = join([f'{time_str(h.comienzo)} a {time_str(h.final)}' for h in horarios])
        aulas = join([f'{h.aula} (P.{h.pabellon})' for h in horarios])
        return TurnoInfo(tipoynumero, f'{dias}: {horas}', aulas)

    def __lt__(self, other):
        if other.__class__ is self.__class__:
            horarios_self = sorted(self.horario_set.all())
            if not horarios_self:
                return True
            horarios_other = sorted(other.horario_set.all())
            if not horarios_other:
                return False
            return horarios_self[0] < horarios_other[0]
        return NotImplemented

    def docentes(self):
        return ' - '.join([f'{carga.docente.nombre}' for carga in self.carga_set.all()])

    def poner_necesidades_segun_alumnos(self):
        if self.tipo == TipoTurno.T.name:
            necesidades = (1, 0, 0, 0)
        elif self.tipo == TipoTurno.A.name:
            necesidades = (1, 1, 1, max(0, int(self.alumnos / 20 - 3)))
        elif self.tipo == TipoTurno.P.name:
            necesidades = (0, 1, 1, max(0, int(self.alumnos / 20 - 2)))
        self.necesidad_prof = necesidades[0]
        self.necesidad_jtp = necesidades[1]
        self.necesidad_ay1 = necesidades[2]
        self.necesidad_ay2 = necesidades[3]
        self.save()


class Horario(models.Model):
    dia = models.CharField(max_length=2, choices=choice_enum(Dias, lambda v: v[0]))
    comienzo = models.TimeField('comienzo')
    final = models.TimeField('final')
    aula = models.CharField(max_length=5, blank=True, null=True)
    pabellon = models.IntegerField(blank=True, null=True)
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.turno}: {self.dia}  {self.comienzo}--{self.final}'

    def __lt__(self, other):
        if other.__class__ is self.__class__:
            return (Dias[self.dia], self.comienzo) < (Dias[other.dia], other.comienzo)
        return NotImplemented


class Docente(models.Model):
    nombre = models.CharField(max_length=60)
    telefono = models.CharField(max_length=15, validators=[int_list_validator(sep=' ')])
    email = models.EmailField()
    cargos = ArrayField(models.CharField(max_length=6, choices=choice_enum(CargoDedicacion)), size=2)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.nombre}'

    @classmethod
    def todos_los(cls, cargo):
        cd = CargoDedicacion.con_cargo(cargo)
        return cls.objects.filter(cargos__overlap=cd)


class Carga(models.Model):
    docente = models.ForeignKey(Docente, on_delete=models.CASCADE)
    cargo = models.CharField(max_length=6, choices=choice_enum(CargoDedicacion))
    anno = models.IntegerField()
    cuatrimestre = models.CharField(max_length=1, choices=choice_enum(Cuatrimestres))
    turno = models.ForeignKey(Turno, null=True, on_delete=models.SET_NULL)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'carga docente'
        verbose_name_plural = 'cargas docentes'

    def __str__(self):
        return f'{self.docente} -> {self.turno}'
