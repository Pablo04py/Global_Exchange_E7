"""
Configuración WSGI para el proyecto principal (core)[cite: 28].

WSGI (Web Server Gateway Interface) es el estándar de Python para desplegar
aplicaciones en servidores web de producción síncronos (Gunicorn, uWSGI, Apache, etc.)[cite: 28].
Expone la variable `application` utilizada por el servidor web[cite: 28].
"""

import os
from django.core.wsgi import get_wsgi_application

# Establece el archivo de configuración predeterminado de Django para el entorno WSGI
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Instancia la aplicación WSGI que responderá a las peticiones del servidor
application = get_wsgi_application()