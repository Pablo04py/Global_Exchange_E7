"""Context processors de la aplicación de notificaciones."""


def notificaciones_context(request):
    """
    Expone las notificaciones recientes y la cantidad de no leídas
    del usuario autenticado en todos los templates.
    """

    if not request.user.is_authenticated:
        return {
            'notificaciones_recientes': [],
            'notificaciones_no_leidas': 0,
        }

    notificaciones_usuario = (
        request.user.notificaciones
        .select_related('notificacion')
        .order_by('-notificacion__fecha_creacion')
    )

    return {
        'notificaciones_recientes': notificaciones_usuario[:5],
        'notificaciones_no_leidas': notificaciones_usuario.filter(
            leida=False
        ).count(),
    }