"""
Pruebas del modo demostración del cierre de caja (solo desarrollo).

Evalúa la función de saldo de demostración y el comando `preparar_demo_cierre`,
que simula la apertura de caja (SCRUM-37) mientras no esté disponible.
"""

from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from arqueos import integracion
from arqueos.demo import saldo_de_demostracion
from arqueos.models import ArqueoCaja
from caja.models import Caja, EstadoCaja, EstadoSesionCaja, SesionCaja
from .apoyo import Usuario


class SaldoDemostracionTestCase(SimpleTestCase):
    """Pruebas de la función de saldo de demostración."""

    @override_settings(DEBUG=True)
    def test_usa_el_monto_inicial_y_usd_fijo(self):
        """Devuelve el monto inicial del turno en PYG y 1.000 USD."""
        turno = SesionCaja(monto_inicial=Decimal('3000000'))
        self.assertEqual(saldo_de_demostracion(turno), {'PYG': Decimal('3000000'), 'USD': Decimal('1000')})

    @override_settings(DEBUG=True)
    def test_sin_monto_inicial_usa_valor_por_defecto(self):
        """Si el turno no tiene monto inicial usa 5.000.000 PYG."""
        self.assertEqual(saldo_de_demostracion(SesionCaja(monto_inicial=0))['PYG'], Decimal('5000000'))

    @override_settings(DEBUG=False)
    def test_bloqueado_sin_debug(self):
        """Con DEBUG=False no devuelve datos de demostración."""
        with self.assertRaises(integracion.ModuloCajaNoDisponible):
            saldo_de_demostracion(SesionCaja(monto_inicial=1))


@override_settings(DEBUG=True)
class PrepararDemoCierreTestCase(TestCase):
    """Pruebas del comando que prepara un turno abierto de demostración."""

    def setUp(self):
        """Crea un cajero y un usuario sin rol de cajero."""
        self.cajero = Usuario.objects.create_user(username='cajero1', roles=['Cajero'])
        Usuario.objects.create_user(username='cliente1', roles=[])

    def _ejecutar(self, username):
        """Ejecuta el comando capturando su salida."""
        call_command('preparar_demo_cierre', username, stdout=StringIO())

    def test_crea_caja_en_uso_y_turno_abierto(self):
        """Crea una caja EN_USO y un turno ABIERTO con monto inicial y fecha de apertura."""
        self._ejecutar('cajero1')
        turno = SesionCaja.objects.get(cajero=self.cajero)
        self.assertEqual(turno.estado, EstadoSesionCaja.ABIERTA)
        self.assertEqual(turno.monto_inicial, Decimal('5000000'))
        self.assertIsNotNone(turno.fecha_apertura)
        self.assertEqual(turno.caja.estado, EstadoCaja.EN_USO)
        self.assertTrue(turno.caja.codigo.startswith('DEMO-'))

    @override_settings(ARQUEO_FUNCION_SALDO='arqueos.demo.saldo_de_demostracion')
    def test_permite_cerrar_la_caja_de_punta_a_punta(self):
        """Con el turno de demo y el saldo de demo, el cajero puede cerrar la caja."""
        self._ejecutar('cajero1')
        self.client.force_login(self.cajero)
        response = self.client.post(reverse('cerrar_caja'), {'saldo_PYG': '5000000', 'saldo_USD': '990'})
        arqueo = ArqueoCaja.objects.get()
        self.assertRedirects(response, reverse('detalle_arqueo', kwargs={'arqueo_id': arqueo.id}))
        self.assertEqual(arqueo.detalles.get(moneda='USD').diferencia, Decimal('-10'))
        self.assertEqual(Caja.objects.get().estado, EstadoCaja.INACTIVA)

    def test_no_duplica_turnos(self):
        """Si el cajero ya tiene un turno asignado o abierto, no crea otro."""
        self._ejecutar('cajero1')
        with self.assertRaises(CommandError):
            self._ejecutar('cajero1')
        self.assertEqual(SesionCaja.objects.count(), 1)

    def test_errores(self):
        """Falla si el usuario no existe o no tiene rol Cajero."""
        for username in ['no_existe', 'cliente1']:
            with self.subTest(username=username), self.assertRaises(CommandError):
                self._ejecutar(username)

    @override_settings(DEBUG=False)
    def test_bloqueado_sin_debug(self):
        """No se ejecuta con DEBUG=False."""
        with self.assertRaises(CommandError):
            self._ejecutar('cajero1')
        self.assertFalse(SesionCaja.objects.exists())
