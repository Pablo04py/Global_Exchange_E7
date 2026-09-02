"""
Módulo de pruebas unitarias para el modelo de datos `Usuario`.

Evalúa la correcta instanciación del usuario personalizado, verificando la persistencia
del identificador SSO de Keycloak y el comportamiento del campo `ArrayField` para roles.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model

# Obtiene dinámicamente el modelo de usuario configurado (usuarios.Usuario)[cite: 24]
Usuario = get_user_model()


class UsuarioModelTestCase(TestCase):
    """
    Pruebas unitarias sobre el modelo `Usuario`.
    
    Garantiza que la extensión de `AbstractUser` almacene correctamente
    los atributos de integración con Keycloak y la lista de roles.
    """

    def test_creacion_usuario_con_roles_y_keycloak_id(self):
        """
        Verifica la creación de un usuario asignando roles y keycloak_id[cite: 24].

        ¿Qué verifica?:
            Comprueba que los valores asignados a 'keycloak_id' y al campo
            'roles' (ArrayField) se guarden y recuperen de forma exacta[cite: 24].

        ¿Por qué?:
            Es crítico asegurar que el modelo soporte el identificador 'sub'
            de Keycloak y que permita múltiples roles simultáneos sin perder
            la integridad de los datos en PostgreSQL[cite: 24].
        """
        # Arrange & Act: Creación del registro en la base de datos de pruebas[cite: 24]
        usuario = Usuario.objects.create_user(
            username="juan_perez",
            email="juan@ejemplo.com",
            password="password123",
            keycloak_id="kc-12345",
            roles=["Cliente", "Cajero"]
        )

        # Assert: Validaciones de campos[cite: 24]
        self.assertEqual(usuario.username, "juan_perez")
        self.assertEqual(usuario.keycloak_id, "kc-12345")
        self.assertIn("Cliente", usuario.roles)
        self.assertIn("Cajero", usuario.roles)
        self.assertEqual(len(usuario.roles), 2)

    def test_usuario_sin_roles_por_defecto(self):
        """
        Verifica la asignación por defecto del campo de roles[cite: 24].

        ¿Qué verifica?:
            Que si un usuario se crea sin especificar roles, la lista por
            defecto sea una lista vacía `[]` y no un valor nulo (`None`)[cite: 24].

        ¿Por qué?:
            Previene errores de tipo `TypeError` al intentar iterar o evaluar
            permisos sobre el campo `roles` cuando un usuario no posee roles asignados[cite: 24].
        """
        # Arrange & Act: Crear usuario sin parámetro de roles[cite: 24]
        usuario = Usuario.objects.create_user(
            username="maria_lopez",
            password="password123"
        )
        
        # Assert: Confirmar valor predeterminado lista vacía[cite: 24]
        self.assertEqual(usuario.roles, [])