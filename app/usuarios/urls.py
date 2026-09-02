"""
Módulo de enrutamiento (URLs) para la aplicación de Usuarios.

Define las rutas de perfil y vistas protegidas por roles.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Muestra los datos de perfil y roles del usuario autenticado
    path('perfil/', views.perfil, name='perfil'),
    
    # Vista de acceso restringido únicamente a usuarios con rol 'Cajero'
    path('zona-cajero/', views.zona_cajero, name='zona_cajero'),
]