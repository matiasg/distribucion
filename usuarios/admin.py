from django.contrib import admin
from django.contrib.auth.models import Group
import django.contrib.auth.admin

from .models import Usuario, Grupo
from .views import FormularioCreacionUsuario, FormularioCambioUsuario

admin.site.unregister([Group])
admin.site.register([Grupo])



class AdminDeUsuario(django.contrib.auth.admin.UserAdmin):
    add_form = FormularioCreacionUsuario
    form = FormularioCambioUsuario
    model = Usuario
    list_display = ['username']

admin.site.register(Usuario, AdminDeUsuario)
