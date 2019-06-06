from django.urls import path

from . import views

app_name = 'materias'
urlpatterns = [
    path('', views.index, name='index'),
    path('administrar', views.administrar, name='administrar'),
    path('administrar_alumnos/<int:anno>/<str:cuatrimestre>',
         views.administrar_alumnos, name='administrar_alumnos'),
    path('administrar_docentes/<int:anno>/<str:cuatrimestre>',
         views.administrar_docentes, name='administrar_docentes'),
    path('<str:anno_cuat>', views.por_anno_y_cuatrimestre, name='por_anno_y_cuatrimestre'),
]
