from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from caja.models import Caja, SesionCaja, EstadoCaja, EstadoSesionCaja, SaldoInicialCaja
from operaciones.models import Moneda
from caja.forms import AperturaCajaForm

User = get_user_model()


class AperturaCajaTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin', password='password123')
        self.cajero = User.objects.create_user(username='cajero1', password='password123')
        
        self.moneda_pyg = Moneda.objects.create(codigo='PYG', nombre='Guaraníes', habilitada=True)
        self.moneda_usd = Moneda.objects.create(codigo='USD', nombre='Dólares', habilitada=True)

        self.caja = Caja.objects.create(
            nombre="Caja Principal",
            codigo="CAJA-01",
            estado=EstadoCaja.DISPONIBLE
        )
        self.sesion = SesionCaja.objects.create(
            caja=self.caja,
            cajero=self.cajero,
            asignado_por=self.admin,
            estado=EstadoSesionCaja.ASIGNADA
        )
        self.url = reverse('caja:aperturar_caja')

    def test_form_valido_dinamico(self):
        form_data = {
            'monto_pyg': 5000000.00,
            'monto_usd': 1000.00,
        }
        form = AperturaCajaForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_apertura_caja_exitosa(self):
        self.client.login(username='cajero1', password='password123')
        response = self.client.post(self.url, {
            'monto_pyg': 5000000.00,
            'monto_usd': 1000.00,
        })
        self.assertRedirects(response, reverse('caja:listar_asignaciones'), fetch_redirect_response=False)

        self.sesion.refresh_from_db()
        self.caja.refresh_from_db()

        self.assertEqual(self.sesion.estado, EstadoSesionCaja.ABIERTA)
        self.assertEqual(self.caja.estado, EstadoCaja.EN_USO)

        saldos = SaldoInicialCaja.objects.filter(sesion=self.sesion)
        self.assertEqual(saldos.count(), 2)
        self.assertEqual(saldos.get(moneda=self.moneda_pyg).monto, 5000000.00)