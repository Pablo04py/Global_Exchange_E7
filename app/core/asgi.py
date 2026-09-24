"""Configuración ASGI del proyecto Global Exchange.

Expone la aplicación ASGI en la variable de módulo ``application``, que usan
los servidores asíncronos (por ejemplo, Uvicorn o Daphne) para ejecutar Django.

Más información: https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = get_asgi_application()
