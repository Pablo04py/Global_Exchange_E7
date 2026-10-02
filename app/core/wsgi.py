"""Configuración WSGI del proyecto Global Exchange.

Expone la aplicación WSGI en la variable de módulo ``application``, que usan
los servidores tradicionales (por ejemplo, Gunicorn) para ejecutar Django.

Más información: https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = get_wsgi_application()
