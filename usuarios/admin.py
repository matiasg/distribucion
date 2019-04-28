from django.contrib import admin
from django.contrib.auth.models import Group
import django.contrib.auth.admin

from .models import Usuario, Grupo

admin.site.unregister([Group])
admin.site.register([Usuario, Grupo])
