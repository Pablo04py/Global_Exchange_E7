"""
Modelos de datos para el módulo de Usuarios.

Define la entidad personalizada `Usuario`, extendiendo la funcionalidad
estándar de Django para interactuar con Keycloak y PostgreSQL.
"""

from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.db import models


class Usuario(AbstractUser):
    """
    Modelo de usuario personalizado que extiende AbstractUser.

    Permite almacenar el ID único del proveedor SSO (Keycloak)
    y sincronizar los roles directamente en un ArrayField de PostgreSQL.

    Attributes:
        keycloak_id (str): Identificador 'sub' del usuario en Keycloak.
        roles (list): Lista de nombres de roles provenientes del token SSO.
    """

    # Identificador único devuelto por Keycloak (claim 'sub')
    keycloak_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    
    # Arreglo nativo de PostgreSQL para almacenar múltiples roles como listas de texto
    roles = ArrayField(models.CharField(max_length=100), default=list, blank=True)