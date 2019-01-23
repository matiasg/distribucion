from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('encuesta', views.encuesta, name='mandar'),
    path('final', views.final, name='final_de_encuesta'),
]

