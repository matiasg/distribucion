from django.forms import ModelForm, CharField, ChoiceField
from django.contrib.postgres.forms import SimpleArrayField, SplitArrayField

from functools import partial

from .models import Docente, CargoDedicacion, choice_enum

CHOICES_CARGOS = [(None, '')] + list(reversed(list(choice_enum(CargoDedicacion))))

class DocenteForm(ModelForm):

    cargo0 = ChoiceField(choices=CHOICES_CARGOS, required=False, label='cargo')
    cargo1 = ChoiceField(choices=CHOICES_CARGOS, required=False, label='segundo cargo')
    cargo2 = ChoiceField(choices=CHOICES_CARGOS, required=False, label='tercer cargo')

    class Meta:
        model = Docente
        exclude = ['cargos']
        labels = {
            'na_nombre': 'Nombre',
            'na_apellido': 'Apellido',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cargos = self.instance.cargos
        for i, c in enumerate(cargos):
            self.fields[f'cargo{i}'].initial = c

    def save(self):
        docente = super().save(commit=False)
        docente.cargos = [self.data[k] for k in ('cargo0', 'cargo1', 'cargo2')
                          if self.data[k]]
        docente.save()
