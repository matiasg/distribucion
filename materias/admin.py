from django.contrib import admin

from .models import Materia, Turno, Horario, Docente, Carga, CuatrimestreDocente

admin.site.register([Materia, Turno, Horario, Docente, Carga, CuatrimestreDocente])
