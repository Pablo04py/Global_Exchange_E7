"""Rutas de la aplicación de notificaciones."""

from django.urls import path

from . import views


app_name = 'notificaciones'


urlpatterns = [
    path(
        '<uuid:notificacion_usuario_id>/leer/',
        views.marcar_leida,
        name='marcar_leida'
    ),

    path(
        'leer-todas/',
        views.marcar_todas_leidas,
        name='marcar_todas_leidas'
    ),
]