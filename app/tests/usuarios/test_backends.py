from django.test import TestCase
from django.contrib.auth import get_user_model
from usuarios.backends import KeycloakOIDCAuthenticationBackend

Usuario = get_user_model()


class KeycloakBackendTestCase(TestCase):

    def setUp(self):
        self.backend = KeycloakOIDCAuthenticationBackend()
        self.claims_mock = {
            "given_name": "Carlos",
            "family_name": "Gómez",
            "email": "carlos@globalexchange.com",
            "realm_access": {
                "roles": ["Administrador General", "Analista Cambiario"]
            }
        }

    def test_sync_datos_actualiza_perfil_y_permisos_admin(self):
        """Verifica que _sync_datos mapee campos, roles e is_superuser correctamente."""
        usuario = Usuario.objects.create_user(username="carlos_g")

        self.backend._sync_datos(usuario, self.claims_mock)
        usuario.refresh_from_db()

        self.assertEqual(usuario.first_name, "Carlos")
        self.assertEqual(usuario.last_name, "Gómez")
        self.assertEqual(usuario.email, "carlos@globalexchange.com")
        self.assertIn("Administrador General", usuario.roles)
        self.assertTrue(usuario.is_staff)
        self.assertTrue(usuario.is_superuser)

    def test_sync_datos_para_usuario_sin_privilegios(self):
        """Verifica que un rol estándar no active is_staff ni is_superuser."""
        usuario = Usuario.objects.create_user(username="cliente_normal")
        claims_cliente = {
            "given_name": "Ana",
            "family_name": "Ruiz",
            "email": "ana@ejemplo.com",
            "realm_access": {"roles": ["Cliente"]}
        }

        self.backend._sync_datos(usuario, claims_cliente)
        usuario.refresh_from_db()

        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        self.assertEqual(usuario.roles, ["Cliente"])