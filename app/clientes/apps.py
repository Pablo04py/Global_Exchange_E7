"""Configuración de la aplicación de Clientes para Django."""

from django.apps import AppConfig


class ClientesConfig(AppConfig):
    """
    Define la configuración básica del módulo 'clientes'.
    
    Attributes:
        name (str): Nombre de la app dentro del proyecto Django.
    """
    # Nombre del módulo dentro del proyecto
    name = 'clientes'