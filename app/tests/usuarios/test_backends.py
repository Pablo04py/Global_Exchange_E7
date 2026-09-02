"""
Módulo de pruebas unitarias para el backend de autenticación `KeycloakOIDCAuthenticationBackend`.

Evalúa la lógica interna de sincronización (`_sync_datos`) entre la información devuelta
por los claims de Keycloak y la base de datos local de PostgreSQL.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from usuarios.backends import KeycloakOIDCAuthenticationBackend

# Obtiene el modelo de usuario
Usuario = get_user_model()


class KeycloakBackendTestCase(TestCase):
    """
    Pruebas asociadas a la sincronización de usuarios desde Keycloak.
    
    Asegura que los datos personales, roles, identificadores y permisos de
    administración se sincronicen correctamente según los 'claims' entregados.
    """

    def setUp(self):
        """
        Configuración del backend y simulador de payload (claims) de Keycloak (Arrange).
        """
        self.backend = KeycloakOIDCAuthenticationBackend()
        
        # Simulación de token/claims de un Administrador enviado por Keycloak
        self.claims_mock = {
            "sub": "kc-uuid-9999",
            "given_name": "Carlos",
            "family_name": "Gómez",
            "email": "carlos@globalexchange.com",
            "realm_access": {
                "roles": ["Administrador General", "Analista Cambiario"]
            }
        }

    def test_sync_datos_actualiza_perfil_permisos_y_keycloak_id(self):
        """
        Verifica la correcta mapeación de atributos para un usuario administrativo.

        ¿Qué verifica?:
            Que el método `_sync_datos` extraiga y guarde 'keycloak_id', datos personales,
            actualice los roles y active los flags `is_staff` e `is_superuser`.

        ¿Por qué?:
            Asegura que si un usuario tiene roles de administración en Keycloak, obtenga
            inmediatamente el nivel de acceso correspondiente dentro del panel de Django.
        """
        # Arrange: Usuario previo en BD
        usuario = Usuario.objects.create_user(username="carlos_g")

        # Act: Ejecuta el método de sincronización con los claims mock
        self.backend._sync_datos(usuario, self.claims_mock)
        usuario.refresh_from_db() # Recarga la instancia desde la base de datos

        # Assert: Verificación de atributos e indicadores de permiso
        self.assertEqual(usuario.keycloak_id, "kc-uuid-9999")
        self.assertEqual(usuario.first_name, "Carlos")
        self.assertEqual(usuario.last_name, "Gómez")
        self.assertEqual(usuario.email, "carlos@globalexchange.com")
        self.assertIn("Administrador General", usuario.roles)
        self.assertTrue(usuario.is_staff)
        self.assertTrue(usuario.is_superuser)

    def test_sync_datos_para_usuario_sin_privilegios(self):
        """
        Verifica la sincronización de usuarios operacionales o clientes ordinarios.

        ¿Qué verifica?:
            Que para un usuario con rol 'Cliente' no se activen los flags `is_staff` ni `is_superuser`.

        ¿Por qué?:
            Evita elevaciones no autorizadas de privilegios, asegurando que solo roles
            administrativos explícitos obtengan acceso al panel interno del sistema.
        """
        # Arrange: Usuario en BD y payload con rol no administrativo
        usuario = Usuario.objects.create_user(username="cliente_normal")
        claims_cliente = {
            "sub": "kc-uuid-1111",
            "given_name": "Ana",
            "family_name": "Ruiz",
            "email": "ana@ejemplo.com",
            "realm_access": {"roles": ["Cliente"]}
        }

        # Act: Sincronización
        self.backend._sync_datos(usuario, claims_cliente)
        usuario.refresh_from_db()

        # Assert: Confirmar que NO tiene accesos de staff o superusuario
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        self.assertEqual(usuario.roles, ["Cliente"])