import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class MainViewsTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        # Usuario mock para probar rutas que requieren autenticación
        self.user = User.objects.create_user(
            username="testuser", 
            password="password123"
        )

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
        self.client.login(username="testuser", password="password123")
        
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
            data=json.dumps({'client_id': 'c1'}), 
            content_type='application/json'
        )
        # Redirige al login de Django
        self.assertEqual(response.status_code, 302)

    def test_select_client_ajax_success(self):
        """Verifica que un usuario autenticado pueda cambiar de cliente activo vía POST."""
        self.client.login(username="testuser", password="password123")
        
        response = self.client.post(
            reverse('select_client'), 
            data=json.dumps({'client_id': 'c2'}), 
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(self.client.session.get('ge_active_client'), 'c2')

    # 4. Pruebas de la Vista de Desarrollo (set_role)
    def test_set_role_updates_session(self):
        """Verifica que en ambiente de desarrollo (DEBUG=True) se pueda cambiar de rol."""
        response = self.client.get(reverse('set_role', kwargs={'role': 'Cajero'}))
        self.assertRedirects(response, '/dashboard/')
        self.assertEqual(self.client.session.get('ge_role'), 'Cajero')