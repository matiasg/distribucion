from django.urls import path

from . import views

app_name = 'dborrador'
urlpatterns = [
    path('', views.index, name='index'),
    path('preparar', views.preparar, name='preparar'),
    path('distribuir', views.distribuir, name='distribuir'),
]


