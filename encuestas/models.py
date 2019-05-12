from django.db import models
from simple_history.models import HistoricalRecords
from django.core.validators import MaxValueValidator, RegexValidator

from materias.models import Turno, Docente, Cuatrimestres, Cargos, choice_enum

class PreferenciasDocente(models.Model):
    docente = models.ForeignKey(Docente, on_delete=models.CASCADE)
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE)
    cargo = models.CharField(max_length=3, choices=choice_enum(Cargos))
    peso = models.FloatField(null=True)
    fecha_encuesta = models.DateTimeField()
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.docente} -- {self.peso} -> {self.turno}'

telefono_validator = RegexValidator(regex=r'^\+?[0-9 -]{9,15}$',
                                    message=("El teléfono debe contener +, -, números, espacios "
                                             "y tener longitud de teléfono"))

class OtrosDatos(models.Model):
    docente = models.ForeignKey(Docente, on_delete=models.CASCADE)
    fecha_encuesta = models.DateTimeField()
    comentario = models.TextField()
    cargas = models.PositiveIntegerField(validators=[MaxValueValidator(3)])
    email = models.EmailField()
    telefono = models.CharField(validators=[telefono_validator], max_length=17, blank=True)
