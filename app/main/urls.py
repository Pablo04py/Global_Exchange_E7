"""
Módulo de enrutamiento (URLs) para la aplicación principal (main).

Define el acceso al Dashboard, el selector de cliente activo mediante AJAX
y la herramienta de cambio de rol para entorno de desarrollo.
"""

from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    # Redirige la raíz del sitio directamente al dashboard
    path('', RedirectView.as_view(url='/dashboard/'), name='home'),
    
    # Vista principal del Dashboard del sistema
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Endpoint AJAX para cambiar el cliente activo en la sesión
    path('select-client/', views.select_client, name='select_client'),
    
    # Ruta de desarrollo para simular roles localmente sin Keycloak
    path('dev/set-role/<str:role>/', views.set_role, name='set_role'),
]