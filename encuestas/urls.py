from django.urls import path

from . import views

app_name = 'encuestas'
urlpatterns = [
    path('', views.index, name='index'),
    path('encuesta/<int:anno>/<str:cuatrimestre>/<str:tipo_docente>',
         views.encuesta, name='encuesta'),
]
