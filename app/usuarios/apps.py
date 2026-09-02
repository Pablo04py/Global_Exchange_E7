"""Configuración de la aplicación de Usuarios para Django."""

from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    """
    Define la configuración básica del módulo 'usuarios'.
    
    Attributes:
        name (str): Nombre de la app dentro del proyecto Django.
    """
    # Nombre de la aplicación registrado en el proyecto
    name = 'usuarios'