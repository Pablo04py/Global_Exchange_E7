from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('admin/', admin.site.urls),
    # Rutas para la autenticación con Keycloak (mozilla-django-oidc)
    path('oidc/', include('mozilla_django_oidc.urls')),
    path('', include('main.urls')),
    #ruta a app usuarios
    path('usuarios/', include('usuarios.urls')),
    #ruta app cliente
    path('clientes/', include('clientes.urls')), 
]
