from django.urls import path

from . import views

app_name = 'materias'
urlpatterns = [
    path('', views.index, name='index'),
    path('administrar', views.administrar, name='administrar'),
    path('administrar_turnos/<int:anno>/<str:cuatrimestre>',
         views.administrar_turnos, name='administrar_turnos'),
    path('<str:anno_cuat>', views.por_anno_y_cuatrimestre, name='por_anno_y_cuatrimestre'),
]
