"""Vistas de la aplicación de notificaciones."""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import NotificacionUsuario


@login_required
@require_POST
def marcar_leida(request, notificacion_usuario_id):
    """
    Marca como leída una notificación perteneciente al usuario actual.
    """

    notificacion_usuario = get_object_or_404(
        NotificacionUsuario,
        id=notificacion_usuario_id,
        usuario=request.user
    )

    if not notificacion_usuario.leida:
        notificacion_usuario.leida = True
        notificacion_usuario.fecha_lectura = timezone.now()

        notificacion_usuario.save(
            update_fields=[
                'leida',
                'fecha_lectura'
            ]
        )

    pendientes = (
        request.user.notificaciones
        .filter(leida=False)
        .count()
    )

    return JsonResponse({
        'status': 'ok',
        'pendientes': pendientes,
    })


@login_required
@require_POST
def marcar_todas_leidas(request):
    """
    Marca como leídas todas las notificaciones pendientes
    del usuario autenticado.
    """

    ahora = timezone.now()

    request.user.notificaciones.filter(
        leida=False
    ).update(
        leida=True,
        fecha_lectura=ahora
    )

    return JsonResponse({
        'status': 'ok',
        'pendientes': 0,
    })