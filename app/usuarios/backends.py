"""Backend de autenticación OIDC con Keycloak."""

from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.contrib.auth.models import Group

class KeycloakOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    """Backend de autenticación que sincroniza usuarios de Keycloak con Django.

    Extiende `OIDCAuthenticationBackend` de mozilla-django-oidc para copiar los
    datos personales y los roles del token al modelo `usuarios.models.Usuario`
    en cada inicio de sesión.
    """
    def create_user(self, claims):
        """Crea el usuario local la primera vez que inicia sesión con Keycloak.

        Args:
            claims: Claims del token OIDC devueltos por Keycloak.

        Returns:
            Usuario: El usuario creado y sincronizado.
        """
        user = super().create_user(claims)
        self._sync_datos(user, claims)
        return user

    def update_user(self, user, claims):
        """Actualiza datos y roles de un usuario existente en cada inicio de sesión.

        Args:
            user: Usuario local a actualizar.
            claims: Claims del token OIDC devueltos por Keycloak.

        Returns:
            Usuario: El usuario actualizado.
        """
        self._sync_datos(user, claims)
        return user

    def _sync_datos(self, user, claims):
        """Copia nombre, email y roles del token al usuario y lo guarda.

        También sincroniza los roles como Grupos de Django y marca como
        `is_staff`/`is_superuser` a los usuarios con rol de administrador.

        Args:
            user: Usuario local a sincronizar.
            claims: Claims del token OIDC (usa `given_name`, `family_name`,
                `email` y `realm_access.roles`).
        """
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