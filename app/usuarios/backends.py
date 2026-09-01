from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.contrib.auth.models import Group
import requests

class KeycloakOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    
    def get_token(self, payload):
        """Envía client_id y client_secret vía HTTP Basic Auth para Keycloak"""
        auth = (self.OIDC_RP_CLIENT_ID, self.OIDC_RP_CLIENT_SECRET)
        
        # Eliminamos client_id y client_secret del body si van en auth
        body_payload = payload.copy()
        body_payload.pop('client_id', None)
        body_payload.pop('client_secret', None)
        
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
        Sobrescribe para unir los claims del ID Token con los de UserInfo,
        asegurando que 'realm_access' siempre esté disponible.
        """
        claims = super().get_userinfo(token_payload.get('access_token'), token_payload.get('id_token'), payload=token_payload)
        return claims

    def create_user(self, claims):
        user = super().create_user(claims)
        self._sync_datos(user, claims)
        return user

    def update_user(self, user, claims):
        self._sync_datos(user, claims)
        return user

    def _sync_datos(self, user, claims):
        user.first_name = claims.get('given_name', '')
        user.last_name = claims.get('family_name', '')
        user.email = claims.get('email', '')

        # Extraer roles del realm de Keycloak
        roles = claims.get('realm_access', {}).get('roles', [])
        
        # Guardar en tu campo de modelo (ArrayField o lista)
        if hasattr(user, 'roles'):
            user.roles = roles

        # Sincronización limpia con Grupos de Django
        if roles:
            user.groups.clear()
            for role_name in roles:
                group, _ = Group.objects.get_or_create(name=role_name)
                user.groups.add(group)

        # Asignación de permisos de administración de Django
        is_admin = any(r in roles for r in ['Administrador General', 'admin', 'Admin'])
        user.is_staff = is_admin
        user.is_superuser = is_admin

        user.save()

    def _sync_datos(self, user, claims):
        user.first_name = claims.get('given_name', '')
        user.last_name = claims.get('family_name', '')
        user.email = claims.get('email', '')
        
        # Vincular el ID único de Keycloak
        if 'sub' in claims:
            user.keycloak_id = claims['sub']

        roles = claims.get('realm_access', {}).get('roles', [])
        
        if hasattr(user, 'roles'):
            user.roles = roles

        if roles:
            user.groups.clear()
            for role_name in roles:
                group, _ = Group.objects.get_or_create(name=role_name)
                user.groups.add(group)

        is_admin = any(r in roles for r in ['Administrador General', 'admin', 'Admin'])
        user.is_staff = is_admin
        user.is_superuser = is_admin

        user.save()