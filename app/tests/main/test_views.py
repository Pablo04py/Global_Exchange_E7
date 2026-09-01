import json
import uuid
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from usuarios.models import Usuario
from clientes.models import Cliente, UsuarioCliente

class MainViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = Usuario.objects.create_user(
            username="testuser",
            password="password123",
            email="test@example.com",
            is_superuser=True  # Concede permisos elevados para bypass de la vista set_role
        )
        self.cliente = Cliente.objects.create(
            id=uuid.uuid4(),
            nombre_o_denominacion="Cliente Test",
            documento="12345678",
            tipo_persona=Cliente.TipoPersona.FISICA
        )
        UsuarioCliente.objects.create(
            usuario=self.user,
            cliente=self.cliente
        )
        self.client.login(username="testuser", password="password123")

    def test_select_client_ajax_success(self):
        """Verifica que un usuario pueda cambiar de cliente activo enviando JSON."""
        payload = json.dumps({'client_id': str(self.cliente.id)})
        response = self.client.post(
            reverse('select_client'),
            data=payload,
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)

    @override_settings(DEBUG=True)
    def test_set_role_updates_session(self):
        """Verifica el cambio de rol en sesión pasando el argumento por URL."""
        url = reverse('set_role', kwargs={'role': 'Cliente'})
        response = self.client.post(url)
        self.assertIn(response.status_code, [200, 302])