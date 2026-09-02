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
        self.cliente_fisico = Cliente.objects.create(
            nombre_o_denominacion="Juan Pérez",
            documento="999888",
            tipo_persona=Cliente.TipoPersona.FISICA
        )
        self.cliente_empresa = Cliente.objects.create(
            nombre_o_denominacion="Empresa S.A.",
            documento="111222",
            tipo_persona=Cliente.TipoPersona.JURIDICA
        )

    def login_usuario(self, usuario):
        """Autentica al usuario forzando el backend para evitar la redirección OIDC de Keycloak."""
        self.client.force_login(usuario, backend='django.contrib.auth.backends.ModelBackend')

    def test_lista_clientes_acceso_administrador(self):
        self.login_usuario(self.admin)
        response = self.client.get(reverse('lista_clientes'))
        self.assertEqual(response.status_code, 200)

    def test_lista_clientes_bloqueo_usuario_comun(self):
        self.login_usuario(self.usuario)
        response = self.client.get(reverse('lista_clientes'))
        self.assertEqual(response.status_code, 403)

    def test_convertirse_en_cliente_crea_relacion(self):
        self.login_usuario(self.usuario)
        response = self.client.post(reverse('convertirse_en_cliente'), {
            'nombre_o_denominacion': 'Normal User',
            'documento': '777666'
        })
        self.assertRedirects(response, reverse('mis_clientes'), fetch_redirect_response=False)
        self.assertTrue(UsuarioCliente.objects.filter(usuario=self.usuario, cliente__tipo_persona=Cliente.TipoPersona.FISICA).exists())

    def test_convertirse_en_cliente_permite_si_solo_tiene_empresa(self):
        UsuarioCliente.objects.create(usuario=self.usuario, cliente=self.cliente_empresa)
        self.login_usuario(self.usuario)
        
        response = self.client.get(reverse('convertirse_en_cliente'))
        self.assertEqual(response.status_code, 200)

    def test_convertirse_en_cliente_bloquea_si_ya_tiene_fisica(self):
        UsuarioCliente.objects.create(usuario=self.usuario, cliente=self.cliente_fisico)
        self.login_usuario(self.usuario)
        
        response = self.client.get(reverse('convertirse_en_cliente'))
        self.assertRedirects(response, reverse('mis_clientes'), fetch_redirect_response=False)

    def test_mis_clientes_filtra_solo_asociados(self):
        UsuarioCliente.objects.create(usuario=self.usuario, cliente=self.cliente_fisico)
        self.login_usuario(self.usuario)
        
        response = self.client.get(reverse('mis_clientes'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.cliente_fisico, response.context['clientes'])
        self.assertNotIn(self.cliente_empresa, response.context['clientes'])

    def test_asignar_cliente_vista_maneja_validation_error(self):
        UsuarioCliente.objects.create(usuario=self.usuario, cliente=self.cliente_fisico)
        self.login_usuario(self.admin)

        otro_usuario = Usuario.objects.create_user(username="otro", password="password123")
        
        response = self.client.post(reverse('asignar_cliente'), {
            'usuario': otro_usuario.id,
            'cliente': self.cliente_fisico.id
        })
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        
        # Extraer los mensajes raw de la lista de errores para evitar el escape de HTML (&#x27;)
        mensajes_error = [error.message for error in form.non_field_errors().as_data()]
        msg_esperado = f"El cliente '{self.cliente_fisico.nombre_o_denominacion}' es Persona Física y ya tiene un usuario asignado."
        
        self.assertIn(msg_esperado, mensajes_error)