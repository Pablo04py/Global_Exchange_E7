"""
Módulo de pruebas unitarias para los decoradores de seguridad.

Evalúa las reglas de Control de Acceso Basado en Roles (RBAC) aplicadas
mediante el decorador `@requiere_rol`.
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from usuarios.decorators import requiere_rol

# Obtiene el modelo de usuario activo[cite: 25]
Usuario = get_user_model()


# Vista falsa (mock) protegida para verificar la ejecución del decorador[cite: 25]
@requiere_rol("Administrador General", "Cajero")
def vista_protegida_mock(request):
    """Vista simulada que solo devuelve HTTP 200 si el decorador otorga acceso."""
    return HttpResponse("Acceso Concedido")


class DecoratorsTestCase(TestCase):
    """
    Conjunto de pruebas para validar el comportamiento del decorador `@requiere_rol`.
    
    Verifica que la restricción de acceso funcione correctamente para usuarios anónimos,
    usuarios sin rol, usuarios con rol vía ArrayField, usuarios con rol vía Grupos de Django
    y superusuarios.
    """

    def setUp(self):
        """
        Configuración inicial del entorno de prueba (Arrange).

        Prepara una fábrica de peticiones HTTP (`RequestFactory`) y crea diferentes
        perfiles de usuario con variaciones de permisos.
        """
        self.factory = RequestFactory()
        
        # Usuario con rol asignado en el ArrayField[cite: 25]
        self.usuario_cajero = Usuario.objects.create_user(
            username="cajero1",
            password="password123",
            roles=["Cajero"]
        )
        
        # Usuario sin rol permitido para la vista simulada[cite: 25]
        self.usuario_cliente = Usuario.objects.create_user(
            username="cliente1",
            password="password123",
            roles=["Cliente"]
        )
        
        # Usuario que obtiene el rol mediante el sistema de Grupos de Django[cite: 25]
        self.usuario_grupo = Usuario.objects.create_user(
            username="grupo1",
            password="password123"
        )
        grupo = Group.objects.create(name="Cajero")
        self.usuario_grupo.groups.add(grupo)

        # Superusuario global[cite: 25]
        self.superuser = Usuario.objects.create_superuser(
            username="super",
            email="super@test.com",
            password="password123"
        )

    def test_usuario_no_autenticado_lanza_permission_denied(self):
        """
        Verifica el rechazo a usuarios no autenticados (Anónimos)[cite: 25].

        ¿Qué verifica?:
            Que una petición realizada por un `AnonymousUser` fuerce la excepción `PermissionDenied` (HTTP 403)[cite: 25].

        ¿Por qué?:
            Evita fugas de seguridad donde usuarios sin iniciar sesión puedan acceder a vistas internas[cite: 25].
        """
        # Act: Simular petición HTTP GET anónima[cite: 25]
        request = self.factory.get("/ruta-protegida/")
        request.user = AnonymousUser()

        # Assert: Debe lanzar PermissionDenied[cite: 25]
        with self.assertRaises(PermissionDenied):
            vista_protegida_mock(request)

    def test_usuario_sin_rol_requerido_lanza_permission_denied(self):
        """
        Verifica el bloqueo de acceso cuando el usuario no cumple los roles requeridos[cite: 25].

        ¿Qué verifica?:
            Que un usuario autenticado pero con un rol distinto (ej. 'Cliente') reciba `PermissionDenied`[cite: 25].

        ¿Por qué?:
            Garantiza que el sistema de permisos restrinja eficazmente las funciones operativas según la jerarquía[cite: 25].
        """
        # Act: Simular petición con usuario de rol 'Cliente'[cite: 25]
        request = self.factory.get("/ruta-protegida/")
        request.user = self.usuario_cliente

        # Assert: Denegar acceso[cite: 25]
        with self.assertRaises(PermissionDenied):
            vista_protegida_mock(request)

    def test_usuario_con_rol_requerido_accede_exitosamente(self):
        """
        Verifica el acceso permitido para un usuario con rol asignado en su ArrayField[cite: 25].

        ¿Qué verifica?:
            Que el usuario con rol 'Cajero' en su lista `user.roles` ejecute la vista y reciba un HTTP 200[cite: 25].

        ¿Por qué?:
            Valida el camino exitoso de acceso basado en el campo personalizado de roles[cite: 25].
        """
        # Act: Ejecución de la vista simulada[cite: 25]
        request = self.factory.get("/ruta-protegida/")
        request.user = self.usuario_cajero

        response = vista_protegida_mock(request)
        
        # Assert: Respuesta exitosa[cite: 25]
        self.assertEqual(response.status_code, 200)

    def test_usuario_accede_por_grupo_django(self):
        """
        Verifica el acceso de usuarios que poseen el rol a través de los Grupos de Django[cite: 25].

        ¿Qué verifica?:
            Que la consulta de roles sea híbrida, permitiendo autorizar al usuario si el rol está asignado a nivel de `user.groups`[cite: 25].

        ¿Por qué?:
            Asegura compatibilidad y retrocompatibilidad con las herramientas administrativas estándar de Django[cite: 25].
        """
        # Act: Petición con usuario en grupo 'Cajero'[cite: 25]
        request = self.factory.get("/ruta-protegida/")
        request.user = self.usuario_grupo
        response = vista_protegida_mock(request)
        
        # Assert: Permitido[cite: 25]
        self.assertEqual(response.status_code, 200)

    def test_superuser_accede_sin_roles_explicitos(self):
        """
        Verifica el acceso irrestricto para superusuarios del sistema[cite: 25].

        ¿Qué verifica?:
            Que un `is_superuser=True` sobrepase la verificación de roles específicos y pueda ejecutar la vista[cite: 25].

        ¿Por qué?:
            Permite que el Administrador General o mantenedor técnico realice cualquier operación sin requerir asignación manual de cada rol[cite: 25].
        """
        # Act: Petición enviada por el superusuario[cite: 25]
        request = self.factory.get("/ruta-protegida/")
        request.user = self.superuser
        response = vista_protegida_mock(request)
        
        # Assert: Acceso concedido[cite: 25]
        self.assertEqual(response.status_code, 200)