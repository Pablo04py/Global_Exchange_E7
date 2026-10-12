from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from caja.models import Caja, SesionCaja, EstadoSesionCaja, EstadoCaja, MovimientoCaja
from operaciones.models import Moneda

User = get_user_model()


class AperturaCajaTests(TestCase):
    def setUp(self):
        self.cajero = User.objects.create_user(
            username="cajero_test",
            email="cajero@example.com",
            password="password123"
        )
        self.caja = Caja.objects.create(codigo="CAJA-01", nombre="Caja 1", estado=EstadoCaja.DISPONIBLE)
        self.sesion = SesionCaja.objects.create(
            caja=self.caja,
            cajero=self.cajero,
            asignado_por=self.cajero,
            estado=EstadoSesionCaja.ASIGNADA
        )
        self.moneda_pyg = Moneda.objects.create(codigo="PYG", nombre="Guaraníes", habilitada=True)
        self.moneda_usd = Moneda.objects.create(codigo="USD", nombre="Dólares", habilitada=True)
        self.url = reverse('caja:apertura_caja')
        self.client.force_login(self.cajero)

    def test_apertura_caja_exitosa_movimientos(self):
        response = self.client.post(self.url, {
            'monto_pyg': 5000000,
            'monto_usd': 500
        })

        self.assertEqual(response.status_code, 302)
        
        # Verificar cambio de estados
        self.sesion.refresh_from_db()
        self.caja.refresh_from_db()
        self.assertEqual(self.sesion.estado, EstadoSesionCaja.ABIERTA)
        self.assertEqual(self.caja.estado, EstadoCaja.EN_USO)

        # Verificar creación de MovimientoCaja usando el código de moneda (ej. 'PYG')
        mov_pyg = MovimientoCaja.objects.get(sesion=self.sesion, moneda=self.moneda_pyg.codigo)
        self.assertEqual(mov_pyg.monto, 5000000)
        self.assertEqual(mov_pyg.tipo, 'APERTURA')
        self.assertEqual(mov_pyg.sentido, 'ENTRADA')

        mov_usd = MovimientoCaja.objects.get(sesion=self.sesion, moneda=self.moneda_usd.codigo)
        self.assertEqual(mov_usd.monto, 500)
        self.assertEqual(mov_usd.tipo, 'APERTURA')
        self.assertEqual(mov_usd.sentido, 'ENTRADA')

    def test_despues_de_la_apertura_la_misma_pantalla_ofrece_el_cierre(self):
        """SCRUM-40: tras abrir, vuelve a la misma pantalla, que ahora muestra el cierre con arqueo ciego."""
        response = self.client.post(self.url, {'monto_pyg': 5000000, 'monto_usd': 500}, follow=True)
        self.assertRedirects(response, self.url)
        self.assertEqual(response.context['modo'], 'cierre')
        self.assertContains(response, 'name="saldo_PYG"')
        self.assertContains(response, 'name="saldo_USD"')
        self.assertNotContains(response, 'name="monto_pyg"')

    def test_muestra_la_apertura_con_turno_asignado(self):
        """Con el turno ASIGNADA, la pantalla muestra el formulario de apertura y no el de cierre."""
        response = self.client.get(self.url)
        self.assertEqual(response.context['modo'], 'apertura')
        self.assertContains(response, 'name="monto_pyg"')
        self.assertNotContains(response, 'Cerrar caja')
