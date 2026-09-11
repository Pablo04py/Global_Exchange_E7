"""
Módulo de enrutamiento (URLs) para la aplicación de Medios de Pago (mpagos).

Mapea las rutas HTTP de la aplicación con sus respectivos controladores/vistas.
"""

from django.urls import path
from . import views

# Namespace para el reverso de URLs en plantillas y redirecciones (ej. 'mpagos:listar')
app_name = 'mpagos'

urlpatterns = [
    # Ruta principal para listar medios de pago activos
    path('', views.listar_medios_pago, name='listar'),
    
    # Ruta para despliegue del formulario de alta
    path('crear/', views.crear_medio_pago, name='crear'),
    
    # Ruta paramétrica para confirmar y procesar la eliminación
    path('eliminar/<int:pk>/', views.eliminar_medio_pago, name='eliminar'),

    # Ruta para acceso directo de edicion de medios de pago
    path('editar/<int:pk>/', views.editar_medio_pago, name='editar'),
]