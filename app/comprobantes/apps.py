"""Configuración de la aplicación comprobantes."""

from django.apps import AppConfig


class ComprobantesConfig(AppConfig):
    """Configuración de Django para la app `comprobantes`."""
    name = 'comprobantes'

    def ready(self):
        """Registra la señal que encola el envío al confirmarse un pago."""
        from . import signals  # noqa: F401
