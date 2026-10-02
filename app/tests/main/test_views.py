import json
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

from clientes.models import Cliente, UsuarioCliente

User = get_user_model()


class MainViewsTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        # Le damos al usuario mock tanto el rol Cliente como Cajero para que pase las validaciones de set_role
        self.user = User.objects.create_user(
            username="testuser", 
            password="password123",
            roles=['Cliente', 'Cajero']
        )
        
        # Crear un cliente real y asociarlo al usuario para pasar las validaciones
        self.cliente = Cliente.objects.create(
            tipo_persona='FISICA', 
            nombre_o_denominacion='Juan Perez', 
            documento='1234567', 
            categoria='MINORISTA'
        )
        UsuarioCliente.objects.create(usuario=self.user, cliente=self.cliente)

    # 1. Pruebas de Redirección y Respuestas HTTP
    def test_home_redirects_to_dashboard(self):
        """Verifica que la URL raíz ('home') redirija a /dashboard/."""
        response = self.client.get(reverse('home'))
        self.assertRedirects(response, '/dashboard/', status_code=302)

    def test_dashboard_renders_successfully_for_anonymous_user(self):
        """Verifica que /dashboard/ responda 200 y use dashboard.html para visitantes."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')
        self.assertEqual(response.context['user_role_label'], 'Visitante')

    # 2. Pruebas del Menú y Contexto según Autenticación y Roles
    def test_dashboard_context_for_authenticated_client(self):
        """Verifica el contexto del dashboard para un usuario logueado con rol 'Cliente'."""
        self.client.force_login(self.user)
        
        session = self.client.session
        session['ge_role'] = 'Cliente'
        session.save()

        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user_role'], 'Cliente')
        self.assertTrue(len(response.context['associated_clients']) > 0)

    # 3. Pruebas del Endpoint AJAX (select_client)
    def test_select_client_requires_login(self):
        """Verifica que usuarios anónimos no puedan cambiar de cliente."""
        response = self.client.post(
            reverse('select_client'), 
            data=json.dumps({'client_id': str(self.cliente.id)}), 
            content_type='application/json'
        )
        # Redirige al login de Django
        self.assertEqual(response.status_code, 302)

    def test_select_client_ajax_success(self):
        """Verifica que un usuario autenticado pueda cambiar de cliente activo vía POST."""
        self.client.force_login(self.user)
        
        response = self.client.post(
            reverse('select_client'), 
            data=json.dumps({'client_id': str(self.cliente.id)}), 
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(self.client.session.get('ge_active_client'), str(self.cliente.id))

# 4. Pruebas de la Vista de Desarrollo (set_role)
    @override_settings(DEBUG=True)
    def test_set_role_updates_session(self):
        """Verifica que en ambiente de desarrollo (DEBUG=True) se pueda cambiar de rol."""
        self.client.force_login(self.user)
        
        response = self.client.get(reverse('set_role', kwargs={'role': 'cajero'}))
        self.assertRedirects(response, '/dashboard/')
        self.assertEqual(self.client.session.get('ge_role'), 'Cajero')