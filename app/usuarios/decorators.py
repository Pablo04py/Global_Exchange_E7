"""Decoradores de control de acceso por rol."""

from django.core.exceptions import PermissionDenied
from functools import wraps


def requiere_rol(*roles_permitidos):
    """Restringe una vista a usuarios con al menos uno de los roles indicados.

    Los roles vienen de Keycloak y se sincronizan en cada inicio de sesión.

    Args:
        *roles_permitidos: Nombres de roles, por ejemplo "cajero" o "admin".

    Raises:
        PermissionDenied: Si el usuario no inició sesión o no tiene un rol permitido.
    """
    def decorador(vista):   #recibe la vista original
        @wraps(vista)  #metadata
        def wrapper(request, *args, **kwargs):          #reemplazar la original
            if not request.user.is_authenticated:
                raise PermissionDenied
            if not any(r in request.user.roles for r in roles_permitidos):
                raise PermissionDenied
            return vista(request, *args, **kwargs)
        return wrapper
    return decorador