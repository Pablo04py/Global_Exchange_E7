from django.urls import path
from . import views

urlpatterns = [
    path('', views.ver_cotizaciones, name='ver_cotizaciones'),
    path('api/', views.api_cotizaciones, name='api_cotizaciones'),
]