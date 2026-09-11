from django.shortcuts import render

from django.http import HttpResponse
from .decorators import requiere_rol
from mozilla_django_oidc.views import OIDCLogoutView
from django.conf import settings



def perfil(request):
    if not request.user.is_authenticated:
        return HttpResponse("No estás logueado.")
    return HttpResponse(f"Hola {request.user.username}. Tus roles: {request.user.roles}")


@requiere_rol('Cajero')
def zona_cajero(request):
    return HttpResponse("Bienvenido, sos Cajero. Esta vista es exclusiva para ese rol.")


class KeycloakOIDCLogoutView(OIDCLogoutView):
    def get_logout_url(self):
        #Se obtiene la url configurada en OIDC_OP_LOGOUT_ENDPOINT
        logout_url = settings.OIDC_OP_LOGOUT_ENDPOINT
        id_token = self.request.session.get('oidc_id_token')
        redirect_uri = self.request.build_absolute_uri('/')

        if id_token:
            return f"{logout_url}?id_token_hint={id_token}&post_logout_redirect_uri={redirect_uri}"
        
        return f"{logout_url}?post_logout_redirect_uri={redirect_uri}"