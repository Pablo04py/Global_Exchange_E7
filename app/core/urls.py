"""
Módulo principal de enrutamiento de URLs del proyecto core[cite: 29].

Distribuye el tráfico y redirige las peticiones hacia las aplicaciones internas
o paquetes de terceros según el prefijo de la ruta ingresada[cite: 29].
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    # Panel de administración predeterminado de Django
    path('admin/', admin.site.urls),
    
    # Rutas para el flujo de autenticación SSO con Keycloak via mozilla-django-oidc
    path('oidc/', include('mozilla_django_oidc.urls')),
    
    # Rutas principales del sitio web (Home, landing pages, etc.)
    path('', include('main.urls')),
    
    # Rutas del módulo de gestión de usuarios y roles
    path('usuarios/', include('usuarios.urls')),
    
    # Rutas del módulo de gestión de clientes
    path('clientes/', include('clientes.urls')), 
]