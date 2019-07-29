from django.forms import ModelForm, widgets, DateTimeField, DateTimeInput

from .models import Docente

class DocenteForm(ModelForm):

    class Meta:
        model = Docente
        fields = '__all__'
        labels = {
            'na_nombre': 'Nombre',
            'na_apellido': 'Apellido',
        }
