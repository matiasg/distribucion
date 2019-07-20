from django.urls import path

from . import views

app_name = 'encuestas'
urlpatterns = [
    path('', views.index, name='index'),
    path('administrar_habilitadas',
         views.administrar_habilitadas, name='administrar_habilitadas'),
    path('encuesta/<int:anno>/<str:cuatrimestres>/<str:tipo_docente>',
         views.encuesta, name='encuesta'),
]
