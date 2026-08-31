from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_clientes, name='lista_clientes'),
    path('nuevo/', views.crear_cliente, name='crear_cliente'),
    path('editar/<uuid:cliente_id>/', views.editar_cliente, name='editar_cliente'),
    path('asignar/', views.asignar_cliente, name='asignar_cliente'),
    path('mis-clientes/', views.mis_clientes, name='mis_clientes'),
    path('convertirse-en-cliente/', views.convertirse_en_cliente, name='convertirse_en_cliente'),
]
