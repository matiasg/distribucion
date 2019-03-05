from django.contrib import admin

from .models import Preferencia, Asignacion

admin.site.register([Preferencia, Asignacion])
