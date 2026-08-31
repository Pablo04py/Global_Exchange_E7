from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.contrib.auth.models import Group

class KeycloakOIDCAuthenticationBackend(OIDCAuthenticationBackend):
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

        roles = claims.get('realm_access', {}).get('roles', [])
        user.roles = roles  # Guarda en tu ArrayField

        # Sincronización con Grupos de Django (Clave para views.py)
        user.groups.clear()
        for role_name in roles:
            group, _ = Group.objects.get_or_create(name=role_name)
            user.groups.add(group)

        # Tolerancia a nombres cortos de Keycloak (admin, Administrador General, etc.)
        is_admin = any(r in roles for r in ['Administrador General', 'admin', 'Admin'])
        user.is_staff = is_admin
        user.is_superuser = is_admin

        user.save()