import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = config('SECRET_KEY', default='dev-secret-key')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', default='localhost 127.0.0.1').split()


INSTALLED_APPS = [
    # Apps nativas de Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'usuarios', 
    
    
    # Librerías de terceros
    'mozilla_django_oidc',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # Apunta a la carpeta /app/templates
        'APP_DIRS': True,
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

WSGI_APPLICATION = 'core.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB', default='globalexchange'),
        'USER': config('POSTGRES_USER', default='pguser'),
        'PASSWORD': config('POSTGRES_PASSWORD', default='pgpassword'),
        'HOST': config('DB_HOST', default='db'),
        'PORT': config('DB_PORT', default='5432'),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-py'
TIME_ZONE = 'America/Asuncion'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


AUTHENTICATION_BACKENDS = (
    'usuarios.backends.KeycloakOIDCAuthenticationBackend',
    'django.contrib.auth.backends.ModelBackend',
)

# Identificación del Cliente Keycloak
OIDC_RP_CLIENT_ID = config('KEYCLOAK_CLIENT_ID', default='django-backend')
OIDC_RP_CLIENT_SECRET = config('KEYCLOAK_CLIENT_SECRET', default='')


AUTH_USER_MODEL = 'usuarios.Usuario'

# Servidores Keycloak (Navegador e Interno Docker)
KEYCLOAK_SERVER_URL_BROWSER = config('KEYCLOAK_SERVER_URL_BROWSER', default='http://localhost:8080')
KEYCLOAK_SERVER_URL_INTERNAL = config('KEYCLOAK_SERVER_URL_INTERNAL', default='http://keycloak:8080')
KEYCLOAK_REALM = config('KEYCLOAK_REALM', default='globalexchange')

# Endpoints OIDC
OIDC_OP_AUTHORIZATION_ENDPOINT = f"{KEYCLOAK_SERVER_URL_BROWSER}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/auth"
OIDC_OP_TOKEN_ENDPOINT = f"{KEYCLOAK_SERVER_URL_INTERNAL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
OIDC_OP_USER_ENDPOINT = f"{KEYCLOAK_SERVER_URL_INTERNAL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/userinfo"
OIDC_OP_JWKS_ENDPOINT = f"{KEYCLOAK_SERVER_URL_INTERNAL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"

# Algoritmo de firma
OIDC_RP_SIGN_ALGO = 'RS256'

# Redirecciones
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
