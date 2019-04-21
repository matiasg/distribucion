from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Materia, Turno, Horario, Docente, Carga, CuatrimestreDocente

admin.site.register([Materia, Carga, Turno, Horario, Docente, CuatrimestreDocente],
                    SimpleHistoryAdmin)
