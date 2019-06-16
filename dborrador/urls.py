from django.urls import path

from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.views import serve
from django.views.decorators.cache import never_cache

from . import views

app_name = 'dborrador'
urlpatterns = [
    path('', views.index, name='index'),
    path('distribucion/<int:anno>/<str:cuatrimestre>/<int:intento_algoritmo>/<int:intento_manual>',
         views.ver_distribucion, name='distribucion'),
    path('empezar',
         views.empezar_a_distribuir, name='empezar'),
    path('cambiar_docente/<int:anno>/<str:cuatrimestre>/<int:intento_algoritmo>/<int:intento_manual>/<int:carga_id>',
         views.cambiar_docente, name='cambiar_docente'),
    path('distribuir/<int:anno>/<str:cuatrimestre>/<str:tipo>/<int:intento_algoritmo>/<int:intento_manual>',
         views.distribuir, name='distribuir'),
    path('preparar/<int:anno>/<str:cuatrimestre>',
         views.preparar, name='preparar'),
    path('predistribuir/<int:anno>/<str:cuatrimestre>/<int:intento_algoritmo>/<int:intento_manual>',
         views.seleccion_tipo_distribuir, name='seleccion_tipo_distribuir'),


    path('fijar/<int:anno>/<str:cuatrimestre>/<str:tipo>/<int:intento_algoritmo>/<int:intento_manual>',
         views.fijar, name='fijar'),
]
