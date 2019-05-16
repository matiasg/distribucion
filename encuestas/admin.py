from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import PreferenciasDocente, OtrosDatos

admin.site.register([PreferenciasDocente], SimpleHistoryAdmin)
admin.site.register([OtrosDatos])
