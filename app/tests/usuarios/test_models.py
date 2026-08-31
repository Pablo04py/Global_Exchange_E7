from django.test import TestCase
from django.contrib.auth import get_user_model

Usuario = get_user_model()


class UsuarioModelTestCase(TestCase):

    def test_creacion_usuario_con_roles_y_keycloak_id(self):
        """Verifica que un usuario se cree correctamente con sus roles y ID de Keycloak."""
        usuario = Usuario.objects.create_user(
            username="juan_perez",
            email="juan@ejemplo.com",
            password="password123",
            keycloak_id="kc-12345",
            roles=["Cliente", "Cajero"]
        )

        self.assertEqual(usuario.username, "juan_perez")
        self.assertEqual(usuario.keycloak_id, "kc-12345")
        self.assertIn("Cliente", usuario.roles)
        self.assertIn("Cajero", usuario.roles)
        self.assertEqual(len(usuario.roles), 2)

    def test_usuario_sin_roles_por_defecto(self):
        """Verifica que si no se asignan roles, la lista por defecto sea vacía."""
        usuario = Usuario.objects.create_user(
            username="maria_lopez",
            password="password123"
        )

        self.assertEqual(usuario.roles, [])