from django.urls import path

from . import views

app_name = 'encuestas'
urlpatterns = [
    path('', views.index, name='index'),
    path('agregar_habilitacion',
         views.agregar_habilitacion, name='agregar_habilitacion'),
    path('cambiar_habilitacion/<int:habilitacion_id>',
         views.cambiar_habilitacion, name='cambiar_habilitacion'),
    path('administrar_habilitadas',
         views.administrar_habilitadas, name='administrar_habilitadas'),
    path('encuesta/<int:anno>/<str:cuatrimestres>/<str:tipo_docente>',
         views.encuesta, name='encuesta'),
]
