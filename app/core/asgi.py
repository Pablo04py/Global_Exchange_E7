"""
Configuración ASGI para el proyecto principal (core)[cite: 30].

ASGI (Asynchronous Server Gateway Interface) es el estándar asíncrono para Python[cite: 30].
Se utiliza para desplegar la aplicación en servidores asíncronos (Daphne, Uvicorn)
y soporte de WebSockets, HTTP2 o tareas asíncronas[cite: 30].
Expone la variable `application`[cite: 30].
"""

import os
from django.core.asgi import get_asgi_application

# Establece el archivo de configuración predeterminado de Django para el entorno ASGI
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Instancia la aplicación ASGI que procesará peticiones asíncronas
application = get_asgi_application()