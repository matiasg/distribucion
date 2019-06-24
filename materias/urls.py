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
    path('administrar_cargas_docentes/<int:anno>/<str:cuatrimestre>',
         views.administrar_cargas_docentes, name='administrar_cargas_docentes'),
    path('administrar_cargas_un_docente/<int:anno>/<str:cuatrimestre>/<int:docente_id>',
         views.administrar_cargas_de_un_docente, name='administrar_cargas_un_docente'),
    path('<str:anno_cuat>', views.por_anno_y_cuatrimestre, name='por_anno_y_cuatrimestre'),
]
