"""
Pruebas del comando `preparar_demo_cierre` (solo desarrollo).

El comando crea una caja y usa los servicios reales de la app `caja` para
asignarla (SCRUM-36) y abrirla (SCRUM-37) con fondo inicial por moneda. El
cierre se hace con el saldo registrado real (`arqueos.saldos`).
"""

from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from arqueos.models import ArqueoCaja
from caja.models import Caja, EstadoCaja, EstadoSesionCaja, SesionCaja, TipoMovimiento
from operaciones.models import Moneda
from .apoyo import Usuario


@override_settings(DEBUG=True)
class PrepararDemoCierreTestCase(TestCase):
    """Pruebas del comando que prepara un turno abierto de demostración."""

    def setUp(self):
        """Crea un cajero, un usuario sin rol de cajero y las monedas habilitadas."""
        self.cajero = Usuario.objects.create_user(username='cajero1', roles=['Cajero'])
        Usuario.objects.create_user(username='cliente1', roles=[])
        Moneda.objects.create(codigo='USD', nombre='Dólar')
        Moneda.objects.create(codigo='EUR', nombre='Euro')

    def _ejecutar(self, username):
        """Ejecuta el comando capturando su salida."""
        call_command('preparar_demo_cierre', username, stdout=StringIO())

    def test_crea_caja_en_uso_y_turno_abierto_con_fondo_inicial(self):
        """Crea una caja EN_USO y un turno ABIERTO con fondo en guaraníes y en cada moneda habilitada."""
        self._ejecutar('cajero1')
        turno = SesionCaja.objects.get(cajero=self.cajero)
        self.assertEqual(turno.estado, EstadoSesionCaja.ABIERTA)
        self.assertEqual(turno.monto_inicial, Decimal('5000000'))
        self.assertIsNotNone(turno.fecha_apertura)
        self.assertEqual(turno.caja.estado, EstadoCaja.EN_USO)
        apertura = turno.movimientos.filter(tipo=TipoMovimiento.APERTURA)
        self.assertEqual(
            {m.moneda: m.monto for m in apertura},
            {'PYG': Decimal('5000000'), 'USD': Decimal('1000'), 'EUR': Decimal('1000')},
        )

    def test_permite_cerrar_la_caja_de_punta_a_punta(self):
        """Con el turno de demo y el saldo registrado real, el cajero cierra la caja."""
        self._ejecutar('cajero1')
        self.client.force_login(self.cajero)
        response = self.client.post(reverse('cerrar_caja'), {
            'saldo_PYG': '5000000', 'saldo_USD': '990', 'saldo_EUR': '1000',
        })
        arqueo = ArqueoCaja.objects.get()
        self.assertRedirects(response, reverse('detalle_arqueo', kwargs={'arqueo_id': arqueo.id}))
        self.assertEqual(arqueo.detalles.get(moneda='USD').diferencia, Decimal('-10'))
        self.assertEqual(arqueo.detalles.get(moneda='PYG').resultado, 'CUADRA')
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
