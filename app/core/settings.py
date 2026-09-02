"""
Configuración central del proyecto Django (core)[cite: 31].

Contiene todas las variables de entorno, base de datos PostgreSQL,
middleware, aplicaciones instaladas e integración con Keycloak (OIDC)[cite: 31].
"""

import os
from pathlib import Path
from decouple import config

# Ruta raíz del proyecto (directorio base)[cite: 31]
BASE_DIR = Path(__file__).resolve().parent.parent

# Clave secreta para la firma criptográfica (se lee desde variables de entorno)[cite: 31]
SECRET_KEY = config('SECRET_KEY', default='dev-secret-key')

# Modo depuración: True en desarrollo, False en producción[cite: 31]
DEBUG = config('DEBUG', default=True, cast=bool)

# Dominio / IPs autorizadas para responder peticiones[cite: 31]
ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', default='localhost 127.0.0.1').split()


# Registro de módulos internos y librerías de terceros activas[cite: 31]
INSTALLED_APPS = [
    # Módulos nativos de Django[cite: 31]
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres', # Soporte para campos avanzados de PostgreSQL
    
    # Módulos propios del proyecto[cite: 31]
    'usuarios', 
    'clientes', 
    'main',
    
    # Módulos de terceros[cite: 31]
    'mozilla_django_oidc', # Cliente para autenticación OpenID Connect / Keycloak
]

# Capas intermedias que procesan peticiones HTTP antes de llegar a las vistas[cite: 31]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', # Manejo de sesiones de usuario[cite: 31]
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware', # Protección contra ataques CSRF[cite: 31]
    'django.contrib.auth.middleware.AuthenticationMiddleware', # Vincula usuarios a la petición[cite: 31]
    'mozilla_django_oidc.middleware.SessionRefresh', # Mantiene o renueva la sesión OIDC[cite: 31]
    'django.contrib.messages.middleware.MessageMiddleware', # Mensajes flash del sistema[cite: 31]
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Archivo maestro de definición de URLs[cite: 31]
ROOT_URLCONF = 'core.urls'

# Configuración del motor de plantillas HTML[cite: 31]
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # Directorio de plantillas globales[cite: 31]
        'APP_DIRS': True, # Busca templates dentro de cada app individual[cite: 31]
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Aplicación WSGI por defecto[cite: 31]
WSGI_APPLICATION = 'core.wsgi.application'


# Conexión a la base de datos PostgreSQL mediante variables de entorno[cite: 31]
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB', default='globalexchange'),
        'USER': config('POSTGRES_USER', default='pguser'),
        'PASSWORD': config('POSTGRES_PASSWORD', default='pgpassword'),
        'HOST': config('DB_HOST', default='db'), # Nombre del contenedor Docker o IP de la BD[cite: 31]
        'PORT': config('DB_PORT', default='5432'),
    }
}


# Validadores de complejidad para contraseñas de usuarios[cite: 31]
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internacionalización y zona horaria local[cite: 31]
LANGUAGE_CODE = 'es-py'
TIME_ZONE = 'America/Asuncion'
USE_I18N = True
USE_TZ = True

# Archivos estáticos (CSS, JS, imágenes)[cite: 31]
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Backends de autenticación: Keycloak primero, fallback al login de Django[cite: 31]
AUTHENTICATION_BACKENDS = (
    'usuarios.backends.KeycloakOIDCAuthenticationBackend',
    'django.contrib.auth.backends.ModelBackend',
)

# Indicar que se usará un modelo de usuario personalizado[cite: 31]
AUTH_USER_MODEL = 'usuarios.Usuario'

# Credenciales de integración del cliente en Keycloak[cite: 31]
OIDC_RP_CLIENT_ID = config('KEYCLOAK_CLIENT_ID', default='django-backend')
OIDC_RP_CLIENT_SECRET = config('KEYCLOAK_CLIENT_SECRET', default='')

# Rutas del servidor Keycloak (separando acceso externo desde el navegador e interno entre contenedores Docker)[cite: 31]
KEYCLOAK_SERVER_URL_BROWSER = config('KEYCLOAK_SERVER_URL_BROWSER', default='http://localhost:8080')
KEYCLOAK_SERVER_URL_INTERNAL = config('KEYCLOAK_SERVER_URL_INTERNAL', default='http://keycloak:8080')
KEYCLOAK_REALM = config('KEYCLOAK_REALM', default='globalexchange')

# Endpoints OIDC configurados según la red interna/externa[cite: 31]
OIDC_OP_AUTHORIZATION_ENDPOINT = f"{KEYCLOAK_SERVER_URL_BROWSER}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/auth"
OIDC_OP_TOKEN_ENDPOINT = f"{KEYCLOAK_SERVER_URL_INTERNAL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
OIDC_OP_USER_ENDPOINT = f"{KEYCLOAK_SERVER_URL_INTERNAL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/userinfo"
OIDC_OP_JWKS_ENDPOINT = f"{KEYCLOAK_SERVER_URL_INTERNAL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
OIDC_OP_LOGOUT_ENDPOINT = f"{KEYCLOAK_SERVER_URL_BROWSER}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/logout"

# Algoritmo de verificación de token e instrucciones de redirección[cite: 31]
OIDC_RP_SIGN_ALGO = 'RS256'
OIDC_STORE_ID_TOKEN = True

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = 'oidc_authentication_init'