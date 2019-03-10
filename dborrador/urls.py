from django.urls import path

from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.views import serve
from django.views.decorators.cache import never_cache

from . import views

app_name = 'dborrador'
urlpatterns = [
    path('', views.index, name='index'),
    path('preparar', views.preparar, name='preparar'),
    path('distribuir', views.distribuir, name='distribuir'),
    path('distribucion/<int:anno>/<str:cuatrimestre>/<int:intento>',
                    views.distribucion, name='distribucion'),
]

# if settings.DEBUG:
#     urlpatterns += static(settings.STATIC_URL, view=never_cache(serve))
