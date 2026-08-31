from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse

from usuarios.decorators import requiere_rol

Usuario = get_user_model()


# Vista de prueba mock para decorar
@requiere_rol("Administrador General", "Cajero")
def vista_protegida_mock(request):
    return HttpResponse("Acceso Concedido")


class DecoratorsTestCase(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.usuario_cajero = Usuario.objects.create_user(
            username="cajero1",
            password="password123",
            roles=["Cajero"]
        )
        self.usuario_cliente = Usuario.objects.create_user(
            username="cliente1",
            password="password123",
            roles=["Cliente"]
        )

    def test_usuario_no_autenticado_lanza_permission_denied(self):
        """Un usuario anónimo debe ser rechazado con PermissionDenied (403)."""
        request = self.factory.get("/ruta-protegida/")
        request.user = AnonymousUser()

        with self.assertRaises(PermissionDenied):
            vista_protegida_mock(request)

    def test_usuario_sin_rol_requerido_lanza_permission_denied(self):
        """Un usuario sin el rol permitido debe recibir PermissionDenied."""
        request = self.factory.get("/ruta-protegida/")
        request.user = self.usuario_cliente

        with self.assertRaises(PermissionDenied):
            vista_protegida_mock(request)

    def test_usuario_con_rol_requerido_accede_exitosamente(self):
        """Un usuario con al menos uno de los roles autorizados debe ejecutar la vista."""
        request = self.factory.get("/ruta-protegida/")
        request.user = self.usuario_cajero

        response = vista_protegida_mock(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Acceso Concedido")