"""Modelos de la aplicación usuarios."""

from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.db import models

class Usuario(AbstractUser):
    """Usuario del sistema, sincronizado con Keycloak ("shadow user").

    Extiende `AbstractUser` de Django. Los datos personales y los roles se
    actualizan en cada inicio de sesión desde el token de Keycloak
    (ver `usuarios.backends.KeycloakOIDCAuthenticationBackend`).

    Attributes:
        keycloak_id: Identificador del usuario en Keycloak (claim `sub`).
        roles: Lista de roles del realm de Keycloak (ArrayField de PostgreSQL).
    """
    keycloak_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    roles = ArrayField(models.CharField(max_length=100), default=list, blank=True)