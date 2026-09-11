"""
Módulo de pruebas de integración para las vistas del módulo Operaciones.

Evalúa permisos por rol (@requiere_rol), respuestas HTTP, contexto,
redirecciones tras POST y la lógica del simulador de conversiones.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from decimal import Decimal
from operaciones.models import Moneda, TasaDeCambio

Usuario = get_user_model()


class OperacionesViewsTestCase(TestCase):
    """Pruebas integrales de controladores y seguridad para Operaciones."""

    def setUp(self):
        """Configuración de roles (grupos), usuarios autenticados y datos iniciales."""
        self.client = Client()

        # Crear Grupos/Roles para el decorador @requiere_rol
        self.grupo_admin, _ = Group.objects.get_or_create(name='Administrador General')
        self.grupo_analista, _ = Group.objects.get_or_create(name='Analista Cambiario')

        # Usuario Administrador
        self.admin_user = Usuario.objects.create_user(
            username="admin_test",
            password="password123",
            is_staff=True
        )
        self.admin_user.groups.add(self.grupo_admin)

        # Usuario Analista
        self.analista_user = Usuario.objects.create_user(
            username="analista_test",
            password="password123"
        )
        self.analista_user.groups.add(self.grupo_analista)

        # Usuario sin rol asignado
        self.sin_rol_user = Usuario.objects.create_user(
            username="sin_rol_test",
            password="password123"
        )

        # Moneda y Tasa base de prueba
        self.moneda = Moneda.objects.create(codigo="USD", nombre="Dólar Estadounidense")
        self.tasa = TasaDeCambio.objects.create(
            moneda=self.moneda,
            tasa_base=Decimal("7500.0000"),
            margen_compra=Decimal("100.0000"),
            margen_venta=Decimal("150.0000")
        )

    def _autenticar_con_rol(self, usuario, rol_nombre):
        """Forza el inicio de sesión del usuario e inyecta el rol en la sesión del cliente de prueba."""
        self.client.force_login(usuario)
        session = self.client.session
        session['user_role'] = rol_nombre
        session.save()

    # ─── PRUEBAS DE SEGURIDAD Y ROLES ─────────────────────────────────────────

    def test_lista_monedas_usuario_sin_rol_denegado(self):
        """Verifica que un usuario sin rol 'Administrador General' no pueda acceder a la lista de monedas."""
        self._autenticar_con_rol(self.sin_rol_user, 'Sin Rol')
        response = self.client.get(reverse('lista_monedas'))
        self.assertNotEqual(response.status_code, 200)

    def test_lista_monedas_admin_exitoso(self):
        """Verifica que el 'Administrador General' pueda listar las monedas."""
        self._autenticar_con_rol(self.admin_user, 'Administrador General')
        response = self.client.get(reverse('lista_monedas'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('monedas', response.context)
        self.assertEqual(len(response.context['monedas']), 1)

    # ─── PRUEBAS CRUD DE MONEDAS ──────────────────────────────────────────────

    def test_crear_moneda_post_exitoso(self):
        """Verifica la creación de una moneda y redirección hacia la asignación de tasa."""
        self._autenticar_con_rol(self.admin_user, 'Administrador General')
        data = {
            'codigo': 'EUR',
            'nombre': 'Euro',
            'habilitada': True
        }
        response = self.client.post(reverse('crear_moneda'), data)

        nueva_moneda = Moneda.objects.get(codigo='EUR')
        self.assertRedirects(response, reverse('crear_tasa_con_moneda', kwargs={'moneda_id': nueva_moneda.id}))

    def test_editar_moneda_post_exitoso(self):
        """Verifica la actualización de los datos de una moneda existente."""
        self._autenticar_con_rol(self.admin_user, 'Administrador General')
        data = {
            'codigo': 'USD',
            'nombre': 'Dólar Americano Modificado',
            'habilitada': True
        }
        response = self.client.post(reverse('editar_moneda', kwargs={'moneda_id': self.moneda.id}), data)

        self.assertRedirects(response, reverse('lista_monedas'))
        self.moneda.refresh_from_db()
        self.assertEqual(self.moneda.nombre, 'Dólar Americano Modificado')

    # ─── PRUEBAS CRUD DE TASAS ────────────────────────────────────────────────

    def test_lista_tasas_analista_exitoso(self):
        """Verifica que el 'Analista Cambiario' tenga acceso a la lista de cotizaciones vigentes."""
        self._autenticar_con_rol(self.analista_user, 'Analista Cambiario')
        response = self.client.get(reverse('lista_tasas'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('tasas_actuales', response.context)

    def test_crear_tasa_post_exitoso(self):
        """Verifica la creación y asignación de una nueva tasa de cambio."""
        self._autenticar_con_rol(self.analista_user, 'Analista Cambiario')
        data = {
            'moneda': str(self.moneda.id),
            'tasa_base': '7600.0000',
            'margen_compra': '120.0000',
            'margen_venta': '160.0000'
        }
        response = self.client.post(reverse('crear_tasa'), data)

        self.assertRedirects(response, reverse('lista_tasas'))

    # ─── PRUEBA DEL SIMULADOR ──────────────────────────────────────────────────

    def test_simulador_calculo_compra_y_venta(self):
        """Verifica que la vista simular realice el cálculo exacto sin requerir autenticación previa."""
        # 1. Simulación de Compra (100 USD * Precio Compra 7400 = 740.000 PYG)
        response_compra = self.client.get(reverse('simulador'), {
            'monto': '100',
            'tasa_id': str(self.tasa.id),
            'tipo_operacion': 'compra'
        })
        self.assertEqual(response_compra.status_code, 200)
        resultado_compra = response_compra.context['resultado']
        self.assertEqual(resultado_compra['monto_destino'], Decimal("740000.0000"))

        # 2. Simulación de Venta (100 USD * Precio Venta 7650 = 765.000 PYG)
        response_venta = self.client.get(reverse('simulador'), {
            'monto': '100',
            'tasa_id': str(self.tasa.id),
            'tipo_operacion': 'venta'
        })
        self.assertEqual(response_venta.status_code, 200)
        resultado_venta = response_venta.context['resultado']
        self.assertEqual(resultado_venta['monto_destino'], Decimal("765000.0000"))