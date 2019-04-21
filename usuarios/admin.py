from django.contrib import admin

from .models import Usuario, Grupo

admin.site.register([Usuario, Grupo])
