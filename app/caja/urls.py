from django.urls import path
from . import views

app_name = 'caja'

urlpatterns = [
    path('asignar/', views.asignar_cajero_view, name='asignar_cajero'),
    path('asignaciones/', views.listar_asignaciones_view, name='listar_asignaciones'),
    path('aperturar/', views.aperturar_caja_view, name='aperturar_caja'),
]