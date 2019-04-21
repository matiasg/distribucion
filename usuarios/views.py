import logging

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm

from .models import Usuario

logger = logging.getLogger(__name__)

class FormularioCreacionUsuario(UserCreationForm):

    class Meta:
        model = Usuario
        fields = ('username', 'groups', 'password1', 'password2')

    def save(self):
        usuario = super().save()
        for grupo in self.cleaned_data['groups']:
            usuario.groups.add(grupo)
        usuario.save()
        return usuario


def agregar(request):
    if request.method == 'POST':
        f = FormularioCreacionUsuario(request.POST)
        if f.is_valid():
            f.save()
            messages.success(request, 'Usuario registrado')
            return redirect('/admin')

    else:
        f = FormularioCreacionUsuario()

    return render(request, 'usuarios/agregar.html', {'form': f})
