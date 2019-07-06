from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Materia, Turno, Horario, Docente, Carga



class HorariosInLine(admin.TabularInline):

    model = Horario


class TurnoAdmin(admin.ModelAdmin):

    inlines = [HorariosInLine]


admin.site.register([Materia, Carga, Docente], SimpleHistoryAdmin)
admin.site.register([Turno], TurnoAdmin)
