from django.urls import path

from . import views

app_name = 'materias'
urlpatterns = [
    path('', views.index, name='index'),
    path('administrar', views.administrar, name='administrar'),
    path('administrar_alumnos/<int:anno>/<str:cuatrimestre>',
         views.administrar_alumnos, name='administrar_alumnos'),
    path('administrar_necesidades_docentes/<int:anno>/<str:cuatrimestre>',
         views.administrar_necesidades_docentes, name='administrar_necesidades_docentes'),
    path('administrar_cargas_docentes/<int:anno>/<str:cuatrimestre>',
         views.administrar_cargas_docentes, name='administrar_cargas_docentes'),
    path('administrar_cargas_publicadas/<int:anno>/<str:cuatrimestre>',
         views.administrar_cargas_publicadas, name='administrar_cargas_publicadas'),
    path('cambiar_una_carga_publicada/<int:carga_id>',
         views.cambiar_una_carga_publicada, name='cambiar_una_carga_publicada'),
    path('administrar_cargas_un_docente/<int:anno>/<str:cuatrimestre>/<int:docente_id>',
         views.administrar_cargas_de_un_docente, name='administrar_cargas_un_docente'),
    path('juntar_materias', views.juntar_materias, name='juntar_materias'),
    path('administrar_materia/<int:materia_id>/<int:anno>/<str:cuatrimestre>',
         views.administrar_materia, name='administrar_materia'),
    path('exportar_informacion/<int:anno>/<str:cuatrimestre>',
         views.exportar_informacion, name='exportar_informacion'),
    path('generar_cuatrimestre/<int:anno>/<str:cuatrimestre>',
         views.generar_cuatrimestre, name='generar_cuatrimestre'),
    path('generar_cargas_docentes/<int:anno>/<str:cuatrimestre>',
         views.generar_cargas_docentes, name='generar_cargas_docentes'),
    path('administrar_docentes',
         views.administrar_docentes, name='administrar_docentes'),
    path('administrar_un_docente/<int:docente_id>',
         views.administrar_un_docente, name='administrar_un_docente'),
    path('borrar_turno/<int:turno_id>', views.borrar_turno, name='borrar_turno'),
    path('cambiar_turno/<int:turno_id>', views.cambiar_turno, name='cambiar_turno'),
    path('borrar_horario/<int:horario_id>', views.borrar_horario, name='borrar_horario'),
    path('<str:anno_cuat>', views.por_anno_y_cuatrimestre, name='por_anno_y_cuatrimestre'),
]
