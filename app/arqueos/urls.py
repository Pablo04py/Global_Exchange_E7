"""Rutas de la aplicación arqueos."""

from django.urls import path
from . import views

urlpatterns = [
    path('cerrar/', views.cerrar_caja, name='cerrar_caja'),
    path('<uuid:arqueo_id>/', views.detalle_arqueo, name='detalle_arqueo'),
]
