from django.core.exceptions import PermissionDenied
from functools import wraps

def requiere_rol(*roles_permitidos):
    def decorador(vista):
        @wraps(vista)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied
            
            # Obtener roles desde el ArrayField y desde los Grupos de Django
            user_roles = set(getattr(request.user, 'roles', []) or [])
            if hasattr(request.user, 'groups'):
                user_roles.update(request.user.groups.values_list('name', flat=True))

            # Permitir si es superusuario o si tiene alguno de los roles permitidos
            if request.user.is_superuser or any(r in user_roles for r in roles_permitidos):
                return vista(request, *args, **kwargs)
                
            raise PermissionDenied
        return wrapper
    return decorador