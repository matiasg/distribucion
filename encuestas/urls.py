from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('encuesta/<int:anno>/<str:cuatrimestre>/<str:tipo_docente>',
         views.encuesta, name='encuesta'),
    path('final', views.final, name='final_de_encuesta'),
]

