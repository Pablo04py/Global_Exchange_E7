"""Rutas de la aplicación arqueos."""

from django.urls import path
from . import views

urlpatterns = [
    path('cerrar/', views.cerrar_caja, name='cerrar_caja'),
    path('<uuid:arqueo_id>/', views.detalle_arqueo, name='detalle_arqueo'),
    path('cajas-bloqueadas/', views.cajas_bloqueadas, name='cajas_bloqueadas'),
    path('cajas-bloqueadas/<str:caja_id>/habilitar/', views.habilitar_caja, name='habilitar_caja'),
    path('reporte/', views.reporte_arqueos, name='reporte_arqueos'),
    path('reporte/exportar/', views.exportar_reporte_csv, name='exportar_reporte_arqueos'),
]
