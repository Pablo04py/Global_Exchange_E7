from django.core.exceptions import PermissionDenied
from functools import wraps


def requiere_rol(*roles_permitidos):
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