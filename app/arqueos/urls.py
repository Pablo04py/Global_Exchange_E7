"""Rutas de la aplicación arqueos."""

from django.urls import path
from . import views

urlpatterns = [
    path('cerrar/', views.cerrar_caja, name='cerrar_caja'),
    path('<uuid:arqueo_id>/', views.detalle_arqueo, name='detalle_arqueo'),
    path('reporte/', views.reporte_arqueos, name='reporte_arqueos'),
    path('reporte/exportar/', views.exportar_reporte_csv, name='exportar_reporte_arqueos'),
]
