from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Materia, Turno, Horario, Docente, Carga, CuatrimestreDocente

admin.site.register([Materia, Horario, Docente, CuatrimestreDocente])
admin.site.register([Carga, Turno], SimpleHistoryAdmin)
