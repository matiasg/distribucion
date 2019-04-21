from django.urls import path

from . import views

app_name = 'usuarios'
urlpatterns = [
    path('usuario/add/', views.agregar, name='agregar'),
]

