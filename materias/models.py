from collections import namedtuple
from functools import total_ordering

from django.db import models
from django.core.validators import int_list_validator, MaxValueValidator, RegexValidator
from django.contrib.postgres.fields import ArrayField
from simple_history.models import HistoricalRecords
from enum import Enum

AnnoCuatrimestre = namedtuple('AC', 'anno cuatrimestre')


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
    Eme = 'Prof. Emerito'
    Hon = 'Prof. Honorario'
    Con = 'Prof. Consulto'
    Ple = 'Prof. Plenario'
    Vis = 'Prof. Visitante'
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


@total_ordering
class TipoDocentes(Enum):

    P = 'Profesor'
    J = 'JTP'
    A1 = 'Ay1'
    A2 = 'Ay2'

    def __ge__(self, otro):
        ordenados = [TipoDocentes.A2, TipoDocentes.A1, TipoDocentes.J, TipoDocentes.P]
        return ordenados.index(self) >= ordenados.index(otro)


class TipoTurno(Enum):
    T = 'Teórica'
    P = 'Práctica'
    A = 'Teórico-Práctica'


class Cuatrimestres(Enum):
    V = 'V'
    P = '1'
    S = '2'


@total_ordering
class TipoMateria(Enum):
    B = 'obligatoria'
    R = 'optativa regular'
    N = 'optativa no regular'

    def __ge__(self, otro):
        ordenados = [TipoMateria.B, TipoMateria.R, TipoMateria.N]
        return ordenados.index(self) >= ordenados.index(otro)


class Pabellon(Enum):
    Uno = ('1', '1')
    Dos = ('2', '2')
    Industrias = ('I', 'Ind')
    Cero_infinito = ('0', '0+∞')


def choice_enum(enum_cls, short_value=(lambda e: e.name), long_value=(lambda e: e.value)):
    return ((short_value(e), long_value(e)) for e in enum_cls)


def get_key_enum(enum_cls):
    return {e.value: e.name for e in enum_cls}


TurnoInfo = namedtuple('TurnoInfo', ['tipoynumero', 'diayhora', 'aula'])


class Materia(models.Model):
    nombre = models.CharField(max_length=120)
    obligatoriedad = models.CharField(max_length=1, choices=choice_enum(TipoMateria),
                                      default=TipoMateria.N.name, blank=False)
    history = HistoricalRecords()

    class Meta:
        ordering = ['obligatoriedad', 'nombre']

    def __str__(self):
        return self.nombre


class AliasDeMateria(models.Model):
    nombre = models.CharField(max_length=120)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)


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

    def str_corto(self):
        numero = f' {self.numero}' if self.numero else ''
        return f'{self.materia.nombre}, {TipoTurno[self.tipo].value}{numero}'

    def horarios_info(self):

        def join(lst):
            distintos = len(set(lst))
            if distintos == 0:
                return ''
            if distintos == 1:
                return lst[0]
            else:
                return f'{ ", ".join(lst[:-1]) } y {lst[-1]}'

        tipo = f'{TipoTurno[self.tipo].value}'
        tipoynumero = f'{tipo} {self.numero}' if self.numero else tipo
        horarios = sorted(self.horario_set.all())
        if horarios:
            dias = join([h.dia for h in horarios])
            horas = join([h.de_a() for h in horarios])
            dias_y_horas = f'{dias}: {horas}'
        else:
            dias_y_horas = ''
        aulas = join([h.aula_y_pabellon() for h in horarios])
        return TurnoInfo(tipoynumero, dias_y_horas, aulas)

    def __lt__(self, other):
        if other.__class__ is self.__class__:
            if other.materia == self.materia:
                horarios_self = sorted(self.horario_set.all())
                if not horarios_self:
                    return True
                horarios_other = sorted(other.horario_set.all())
                if not horarios_other:
                    return False
                return horarios_self[0] < horarios_other[0]
            else:
                return self.materia.nombre < other.materia.nombre
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
    dia = models.CharField(max_length=2, choices=choice_enum(Dias, long_value=(lambda e: e.value[0])))
    comienzo = models.TimeField('comienzo')
    final = models.TimeField('final')
    aula = models.CharField(max_length=5, blank=True, null=True)
    pabellon = models.CharField(max_length=1, blank=True, null=True,
                                choices=choice_enum(Pabellon,
                                                    short_value=(lambda e: e.value[0]),
                                                    long_value=(lambda e: e.value[1])))
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.turno}: {self.dia}  {self.comienzo}--{self.final}'

    def __lt__(self, other):
        if other.__class__ is self.__class__:
            return (Dias[self.dia], self.comienzo) < (Dias[other.dia], other.comienzo)
        return NotImplemented

    def de_a(self):

        def time_str(hms):
            if hms.minute:
                return f'{hms.hour}:{hms.minute:02d}'
            return f'{hms.hour}'

        return f'{time_str(self.comienzo)} a {time_str(self.final)}'

    def aula_y_pabellon(self):
        if self.pabellon and self.aula:
            pab = [p for p in Pabellon if p.value[0] == self.pabellon][0]
            return f'{self.aula} (P.{pab.value[1]})'
        else:
            return ''


telefono_validator = RegexValidator(regex=r'^\+?[0-9 -]{9,15}$',
                                    message=('El celular debe ser del estilo "area número" (por ejemplo, +11 1234-5678)'))

class Docente(models.Model):
    na_nombre = models.CharField(max_length=30)
    na_apellido = models.CharField(max_length=30)
    telefono = models.CharField(max_length=17, validators=[telefono_validator], blank=True)
    email = models.EmailField(blank=True)
    cargos = ArrayField(models.CharField(max_length=6, choices=choice_enum(CargoDedicacion)), size=2)
    history = HistoricalRecords()

    class Meta:
        ordering = ['cargos', 'na_apellido', 'na_nombre']

    def __str__(self):
        return f'{self.nombre}'

    @property
    def nombre(self):
        return f'{self.na_nombre} {self.na_apellido}'

    @property
    def apellido_nombre(self):
        return f'{self.na_apellido}, {self.na_nombre}'

    @classmethod
    def todos_los(cls, cargo):
        cd = CargoDedicacion.con_cargo(cargo)
        return cls.objects.filter(cargos__overlap=cd)

    @property
    def cargos_largos(self):
        return [CargoDedicacion[cd].value for cd in self.cargos]


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
        ordering = ['cargo', 'docente__na_appellido', 'docente__na_nombre']

    def __str__(self):
        return f'{self.docente} -> {self.turno}'

    @classmethod
    def para_ac(cls, ac):
        ''' AnnoCuatrimestre -> [Carga] '''
        return cls.objects.filter(anno=ac.anno, cuatrimestre=ac.cuatrimestre)
