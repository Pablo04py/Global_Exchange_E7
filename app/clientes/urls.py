"""
Módulo de enrutamiento (URLs) para la aplicación de Clientes.

Define las rutas públicas y de administración para el flujo de
creación, edición, consulta y asignación de clientes.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Muestra la lista completa de clientes (pantalla de administración)
    path('', views.lista_clientes, name='lista_clientes'),
    
    # Formulario para registrar un nuevo cliente desde el panel de administración
    path('nuevo/', views.crear_cliente, name='crear_cliente'),
    
    # Formulario para editar un cliente existente usando su UUID por la URL
    path('editar/<uuid:cliente_id>/', views.editar_cliente, name='editar_cliente'),
    
    # Formulario para vincular un usuario a un cliente de la base de datos
    path('asignar/', views.asignar_cliente, name='asignar_cliente'),
    
    # Vista donde el usuario logueado ve sus propias cuentas/empresas asociadas
    path('mis-clientes/', views.mis_clientes, name='mis_clientes'),
    
    # Ruta para que un usuario registrado cree su propia cuenta de cliente (Persona Física)
    path('convertirse-en-cliente/', views.convertirse_en_cliente, name='convertirse_en_cliente'),
]