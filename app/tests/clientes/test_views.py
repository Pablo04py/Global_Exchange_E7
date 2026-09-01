from django.test import TestCase
from django.urls import reverse
from usuarios.models import Usuario
from clientes.models import Cliente, UsuarioCliente

class ClienteViewsTest(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            username="admin_user",
            email="admin@test.com",
            password="password123",
            roles=['Administrador General']
        )
        self.usuario = Usuario.objects.create_user(
            username="normal_user",
            email="user@test.com",
            password="password123"
        )
        self.cliente = Cliente.objects.create(
            nombre_o_denominacion="Cliente Test",
            documento="999888",
            tipo_persona=Cliente.TipoPersona.FISICA
        )

    def test_convertirse_en_cliente_crea_relacion(self):
        """Un usuario sin cliente puede registrarse como Persona Física."""
        self.client.force_login(self.usuario)
        response = self.client.post(reverse('convertirse_en_cliente'), {
            'nombre_o_denominacion': 'Normal User',
            'documento': '777666'
        })
        self.assertRedirects(response, reverse('mis_clientes'))
        self.assertTrue(UsuarioCliente.objects.filter(usuario=self.usuario).exists())

    def test_convertirse_en_cliente_redirige_si_ya_tiene(self):
        """Si ya está asociado a un cliente, no permite el acceso a la vista."""
        UsuarioCliente.objects.create(usuario=self.usuario, cliente=self.cliente)
        self.client.force_login(self.usuario)
        response = self.client.get(reverse('convertirse_en_cliente'))
        self.assertRedirects(response, reverse('mis_clientes'))

    def test_mis_clientes_filtra_solo_asociados(self):
        """Verifica que el usuario solo vea los clientes a los que está asociado."""
        UsuarioCliente.objects.create(usuario=self.usuario, cliente=self.cliente)
        self.client.force_login(self.usuario)
        response = self.client.get(reverse('mis_clientes'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.cliente, response.context['clientes'])