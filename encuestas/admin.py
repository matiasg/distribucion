from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import PreferenciasDocente

admin.site.register([PreferenciasDocente], SimpleHistoryAdmin)
