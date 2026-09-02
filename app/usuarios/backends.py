"""
Backend personalizado de autenticación para la integración con Keycloak mediante OIDC.

Gestión del intercambio de tokens, sincronización automática de usuarios,
roles y grupos de permisos dentro del sistema Django.
"""

from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.contrib.auth.models import Group
import requests


class KeycloakOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    """
    Backend OIDC ajustado para comunicarse con el servidor Keycloak.

    Realiza la autenticación mediante HTTP Basic Auth para la obtención del token,
    extrae los datos del usuario ('claims') y sincroniza la información de perfil,
    roles y permisos administrativos en la base de datos de Django.
    """

    def get_token(self, payload):
        """
        Intercambia el código de autorización por el Access Token enviando
        las credenciales de cliente vía HTTP Basic Auth.

        Args:
            payload (dict): Parámetros requeridos para el endpoint de token.

        Returns:
            dict: Respuesta JSON conteniendo los tokens del proveedor SSO.
        """
        # Formatea credenciales de cliente para autenticación Basic Auth
        auth = (self.OIDC_RP_CLIENT_ID, self.OIDC_RP_CLIENT_SECRET)
        
        # Elimina credenciales del cuerpo de la petición si viajan en los encabezados HTTP
        body_payload = payload.copy()
        body_payload.pop('client_id', None)
        body_payload.pop('client_secret', None)
        
        # Petición POST al endpoint de Keycloak para obtener los tokens
        response = requests.post(
            self.OIDC_OP_TOKEN_ENDPOINT,
            data=body_payload,
            auth=auth,
            verify=self.get_settings('OIDC_VERIFY_SSL', True)
        )
        self.raise_token_response_error(response)
        return response.json()

    def get_all_claims(self, token_payload):
        """
        Obtiene los claims unificados del usuario asegurando la inclusión
        de los permisos globales ('realm_access').

        Args:
            token_payload (dict): Payload que contiene el id_token y el access_token.

        Returns:
            dict: Diccionario completo de claims recibidos desde Keycloak.
        """
        # Invoca la extracción de claims mediante la librería OIDC base
        claims = super().get_userinfo(token_payload.get('access_token'), token_payload.get('id_token'), payload=token_payload)
        return claims

    def create_user(self, claims):
        """
        Crea un nuevo usuario local la primera vez que inicia sesión vía Keycloak.

        Args:
            claims (dict): Información entregada por el servidor OIDC.

        Returns:
            Usuario: Instancia del modelo de usuario recién creada.
        """
        user = super().create_user(claims)
        self._sync_datos(user, claims)
        return user

    def update_user(self, user, claims):
        """
        Actualiza los datos del usuario en cada inicio de sesión subsiguiente.

        Args:
            user (Usuario): Instancia del usuario en la BD local.
            claims (dict): Información actualizada entregada por Keycloak.

        Returns:
            Usuario: Instancia del usuario actualizada.
        """
        self._sync_datos(user, claims)
        return user

    def _sync_datos(self, user, claims):
        """
        Método auxiliar que sincroniza los campos del modelo, roles, grupos
        y estatus de administración basándose en los claims recibidos.

        Args:
            user (Usuario): Objeto usuario a actualizar.
            claims (dict): Diccionario de atributos del usuario en Keycloak.
        """
        # Sincronización de información personal básica
        user.first_name = claims.get('given_name', '')
        user.last_name = claims.get('family_name', '')
        user.email = claims.get('email', '')
        
        # Vincular el identificador único de Keycloak (claim 'sub')
        if 'sub' in claims:
            user.keycloak_id = claims['sub']

        # Extracción de roles desde la estructura del realm de Keycloak
        roles = claims.get('realm_access', {}).get('roles', [])
        
        # Almacena la lista de roles en el campo personalizado del modelo
        if hasattr(user, 'roles'):
            user.roles = roles

        # Reemplaza y mapea de forma limpia los roles a Grupos de Django
        if roles:
            user.groups.clear()
            for role_name in roles:
                group, _ = Group.objects.get_or_create(name=role_name)
                user.groups.add(group)

        # Otorga privilegios de staff y superusuario si cuenta con roles administrativos
        is_admin = any(r in roles for r in ['Administrador General', 'admin', 'Admin'])
        user.is_staff = is_admin
        user.is_superuser = is_admin

        # Guarda todos los cambios en la base de datos de PostgreSQL
        user.save()