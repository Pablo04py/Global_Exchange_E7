from mozilla_django_oidc.auth import OIDCAuthenticationBackend

class KeycloakOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    def create_user(self, claims):
        """Se ejecuta la primera vez que un cliente se registra/autentica."""
        # Crea el usuario base en Django
        user = super().create_user(claims)
        
        # Asigna datos personales desde Keycloak
        user.first_name = claims.get('given_name', '')
        user.last_name = claims.get('family_name', '')
        user.email = claims.get('email', '')
        
        # Ejemplo: Asignar superusuario si tiene el rol 'admin' en Keycloak
        roles = claims.get('realm_access', {}).get('roles', [])
        if 'admin' in roles:
            user.is_staff = True
            user.is_superuser = True
            
        user.save()
        return user

    def update_user(self, user, claims):
        """Mantiene los datos y roles actualizados en cada inicio de sesión."""
        user.first_name = claims.get('given_name', '')
        user.last_name = claims.get('family_name', '')
        user.email = claims.get('email', '')
        
        # Sincroniza roles de Keycloak a Django en tiempo real
        roles = claims.get('realm_access', {}).get('roles', [])
        user.is_staff = 'admin' in roles
        user.is_superuser = 'admin' in roles
        
        user.save()
        return user