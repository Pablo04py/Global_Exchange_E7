"""Configuración de la aplicación principal (main) del proyecto."""

from django.apps import AppConfig


class MainConfig(AppConfig):
    """
    Define la configuración básica del módulo 'main'.
    
    Attributes:
        name (str): Nombre de la app dentro del proyecto Django.
    """
    # Nombre del módulo principal dentro del proyecto
    name = 'main'