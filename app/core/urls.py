"""Enrutamiento raíz del proyecto Global Exchange.

Incluye las URLs de cada aplicación y las rutas de autenticación OIDC con Keycloak:

- `admin/`: panel de administración de Django.
- `oidc/`: inicio de sesión y callback de `mozilla-django-oidc`, y cierre de sesión con Keycloak.
- `''`: dashboard y utilidades de la app `main`.
- `usuarios/`, `clientes/`, `medios-pago/`, `cotizaciones/`, `operaciones/`: rutas de cada app.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from usuarios.views import KeycloakOIDCLogoutView

urlpatterns = [
    #path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('admin/', admin.site.urls),
    # Rutas para la autenticación con Keycloak (mozilla-django-oidc)
    path('oidc/', include('mozilla_django_oidc.urls')),
    path('oidc/logout/', KeycloakOIDCLogoutView.as_view(), name='oidc_logout'),
    path('', include('main.urls')),
    #ruta a app usuarios
    path('usuarios/', include('usuarios.urls')),
    #ruta app cliente
    path('clientes/', include('clientes.urls')),
    #ruta app mpagos
    path('medios-pago/', include('mpagos.urls', namespace='mpagos')),
    path('clientes/', include('clientes.urls')), 
    path('cotizaciones/', include('cotizaciones.urls')),
    #ruta a operaciones
    path('operaciones/', include('operaciones.urls')),
]
