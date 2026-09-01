from django.test import TestCase
from django.core.exceptions import ValidationError
from usuarios.models import Usuario
from clientes.models import Cliente, UsuarioCliente

class UsuarioClienteModelTest(TestCase):
    def setUp(self):
        self.usuario1 = Usuario.objects.create_user(username="user1", password="password123")
        self.usuario2 = Usuario.objects.create_user(username="user2", password="password123")

        self.cliente_fisico = Cliente.objects.create(
            nombre_o_denominacion="Juan Pérez",
            documento="123456",
            tipo_persona=Cliente.TipoPersona.FISICA
        )
        self.cliente_juridico = Cliente.objects.create(
            nombre_o_denominacion="Empresa S.A.",
            documento="654321-0",
            tipo_persona=Cliente.TipoPersona.JURIDICA
        )

    def test_asociacion_cliente_fisico_exito(self):
        """Verifica que se pueda asociar 1 usuario a un cliente Persona Física."""
        asociacion = UsuarioCliente.objects.create(
            usuario=self.usuario1,
            cliente=self.cliente_fisico
        )
        self.assertEqual(asociacion.usuario, self.usuario1)
        self.assertEqual(asociacion.cliente, self.cliente_fisico)

    def test_asociacion_cliente_fisico_rebote_segundo_usuario(self):
        """Verifica que rechace asignar un 2º usuario a un cliente Persona Física."""
        UsuarioCliente.objects.create(usuario=self.usuario1, cliente=self.cliente_fisico)
        
        asociacion_invalida = UsuarioCliente(usuario=self.usuario2, cliente=self.cliente_fisico)
        with self.assertRaises(ValidationError):
            asociacion_invalida.full_clean()

    def test_asociacion_duplicada_mismo_usuario_mismo_cliente(self):
        """Verifica que no se pueda duplicar exactamente la misma relación (unique_together)."""
        UsuarioCliente.objects.create(usuario=self.usuario1, cliente=self.cliente_juridico)
        
        duplicado = UsuarioCliente(usuario=self.usuario1, cliente=self.cliente_juridico)
        with self.assertRaises(ValidationError):
            duplicado.full_clean()

    def test_asociacion_cliente_juridico_multiples_usuarios(self):
        """Verifica que un cliente Persona Jurídica acepte N usuarios asociados."""
        UsuarioCliente.objects.create(usuario=self.usuario1, cliente=self.cliente_juridico)
        UsuarioCliente.objects.create(usuario=self.usuario2, cliente=self.cliente_juridico)

        self.assertEqual(self.cliente_juridico.usuarios_asociados.count(), 2)

    def test_usuario_asociado_a_multiples_clientes(self):
        """Verifica que 1 mismo usuario pueda estar en su cuenta personal y empresas."""
        UsuarioCliente.objects.create(usuario=self.usuario1, cliente=self.cliente_fisico)
        UsuarioCliente.objects.create(usuario=self.usuario1, cliente=self.cliente_juridico)

        self.assertEqual(self.usuario1.clientes_asociados.count(), 2)