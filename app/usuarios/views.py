"""Vistas de la aplicación usuarios (perfil, pruebas de rol y logout de Keycloak)."""

from django.shortcuts import render

from django.http import HttpResponse
from .decorators import requiere_rol
from mozilla_django_oidc.views import OIDCLogoutView
from django.conf import settings



def perfil(request):
    """Muestra el nombre de usuario y los roles del usuario autenticado.

    Args:
        request: Petición HTTP.

    Returns:
        HttpResponse: Texto con el usuario y sus roles, o un aviso si no inició sesión.
    """
    if not request.user.is_authenticated:
        return HttpResponse("No estás logueado.")
    return HttpResponse(f"Hola {request.user.username}. Tus roles: {request.user.roles}")


@requiere_rol('Cajero')
def zona_cajero(request):
    """Vista de prueba accesible solo para usuarios con rol `Cajero`.

    Args:
        request: Petición HTTP.

    Returns:
        HttpResponse: Mensaje de bienvenida para el cajero.
    """
    return HttpResponse("Bienvenido, sos Cajero. Esta vista es exclusiva para ese rol.")


class KeycloakOIDCLogoutView(OIDCLogoutView):
    """Vista de cierre de sesión que también cierra la sesión en Keycloak."""
    def get_logout_url(self):
        """Construye la URL de logout de Keycloak.

        Incluye el `id_token_hint` (si existe en la sesión) y la redirección
        de vuelta a la página principal del sistema.

        Returns:
            str: URL del endpoint de logout de Keycloak con sus parámetros.
        """
        #Se obtiene la url configurada en OIDC_OP_LOGOUT_ENDPOINT
        logout_url = settings.OIDC_OP_LOGOUT_ENDPOINT
        id_token = self.request.session.get('oidc_id_token')
        redirect_uri = self.request.build_absolute_uri('/')

        if id_token:
            return f"{logout_url}?id_token_hint={id_token}&post_logout_redirect_uri={redirect_uri}"
        
        return f"{logout_url}?post_logout_redirect_uri={redirect_uri}"