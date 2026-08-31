from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class KeycloakOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    def create_user(self, claims):
        """Se ejecuta la primera vez que un usuario se registra/autentica."""
        user = super().create_user(claims)
        self._sync_datos(user, claims)
        return user

    def update_user(self, user, claims):
        """Mantiene los datos y roles actualizados en cada inicio de sesión."""
        self._sync_datos(user, claims)
        return user

    def _sync_datos(self, user, claims):
        user.first_name = claims.get('given_name', '')
        user.last_name = claims.get('family_name', '')
        user.email = claims.get('email', '')

        roles = claims.get('realm_access', {}).get('roles', [])
        user.roles = roles  # requiere el campo ArrayField en el modelo Usuario

        user.is_staff = 'Administrador General' in roles
        user.is_superuser = 'Administrador General' in roles

        user.save()