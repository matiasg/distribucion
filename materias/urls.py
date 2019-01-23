from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('<str:anno_cuat>', views.por_anno_y_cuatrimestre, name='por_anno_y_cuatrimestre'),
]
