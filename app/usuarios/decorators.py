"""
Decoradores personalizados para el control de acceso basado en roles (RBAC).
"""

from django.core.exceptions import PermissionDenied
from functools import wraps


def requiere_rol(*roles_permitidos):
    """
    Decorador para restringir el acceso a vistas según los roles del usuario.

    Verifica tanto los roles del ArrayField (`user.roles`) como los asignados
    mediante Grupos de Django (`user.groups`). Otorga acceso total si el usuario
    es superusuario (`is_superuser`).

    Args:
        *roles_permitidos (str): Nombres de los roles con permiso de acceso.

    Raises:
        PermissionDenied: Si el usuario no está autenticado o carece de los roles requeridos.
    """
    def decorador(vista):
        @wraps(vista)
        def wrapper(request, *args, **kwargs):
            # Exige sesión activa antes de validar roles
            if not request.user.is_authenticated:
                raise PermissionDenied
            
            # Obtener roles desde el ArrayField y consolidarlos con los Grupos de Django
            user_roles = set(getattr(request.user, 'roles', []) or [])
            if hasattr(request.user, 'groups'):
                user_roles.update(request.user.groups.values_list('name', flat=True))

            # Permitir acceso si es superusuario o si cumple con al menos un rol requerido
            if request.user.is_superuser or any(r in user_roles for r in roles_permitidos):
                return vista(request, *args, **kwargs)
                
            # Si no cumple ningún criterio, deniega el acceso (HTTP 403)
            raise PermissionDenied
        return wrapper
    return decorador