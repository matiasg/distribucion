from django.urls import path

from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.views import serve
from django.views.decorators.cache import never_cache

from . import views

app_name = 'dborrador'
urlpatterns = [
    path('', views.index, name='index'),
    path('preparar', views.preparar, name='preparar'),
    path('distribuir/<int:anno>/<str:cuatrimestre>/<str:tipo>/<int:intento>',
         views.distribuir, name='distribuir'),
    path('distribucion/<int:anno>/<str:cuatrimestre>/<str:tipo>/<int:intento>',
         views.distribucion, name='distribucion'),
    path('fijar/<int:anno>/<str:cuatrimestre>/<str:tipo>/<int:intento>',
         views.fijar, name='fijar'),
]

# if settings.DEBUG:
#     urlpatterns += static(settings.STATIC_URL, view=never_cache(serve))
