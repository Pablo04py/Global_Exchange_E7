"""
Pruebas del saldo registrado del arqueo (`arqueos.saldos`).

Usa los modelos y servicios reales de la app `caja`: el fondo inicial de la
apertura (`SaldoInicialCaja`, SCRUM-37) y los movimientos de efectivo del
turno (`MovimientoCaja`, SCRUM-39).
"""

from decimal import Decimal

from django.test import TestCase

from arqueos.saldos import saldo_inicial, saldo_registrado
from caja.models import MovimientoCaja, SaldoInicialCaja, SentidoMovimiento, TipoMovimiento
from operaciones.models import Moneda
from .apoyo import CajaDePruebaMixin


class SaldoRegistradoTestCase(CajaDePruebaMixin, TestCase):
    """Pruebas del cálculo: fondo inicial + entradas - salidas, por moneda."""

    def setUp(self):
        """Abre el turno con 5.000.000 PYG (monto inicial) y 1.000 USD / 0 EUR de fondo."""
        super().setUp()
        self.usd = Moneda.objects.create(codigo='USD', nombre='Dólar')
        self.eur = Moneda.objects.create(codigo='EUR', nombre='Euro')
        SaldoInicialCaja.objects.create(sesion=self.turno, moneda=self.usd, monto=Decimal('1000'))
        SaldoInicialCaja.objects.create(sesion=self.turno, moneda=self.eur, monto=Decimal('0'))

    def _movimiento(self, sentido, moneda, monto, tipo=TipoMovimiento.OPERACION):
        """Registra un movimiento de efectivo en el turno."""
        MovimientoCaja.objects.create(sesion=self.turno, tipo=tipo, sentido=sentido, moneda=moneda, monto=monto)

    def test_sin_operaciones_es_el_fondo_inicial(self):
        """Sin movimientos, el saldo registrado es el fondo inicial (incluido el guaraní)."""
        self.assertEqual(saldo_registrado(self.turno), {
            'PYG': Decimal('5000000'), 'USD': Decimal('1000'), 'EUR': Decimal('0'),
        })

    def test_suma_entradas_y_resta_salidas(self):
        """Una venta de 100 USD a 7.400: entra la divisa y sale el efectivo en guaraníes."""
        self._movimiento(SentidoMovimiento.ENTRADA, 'USD', Decimal('100'))
        self._movimiento(SentidoMovimiento.SALIDA, 'PYG', Decimal('740000'))
        saldo = saldo_registrado(self.turno)
        self.assertEqual(saldo['USD'], Decimal('1100'))
        self.assertEqual(saldo['PYG'], Decimal('4260000'))

    def test_no_cuenta_dos_veces_si_la_apertura_registra_movimientos(self):
        """Si la apertura ya registró movimientos de tipo APERTURA, no se vuelve a sumar el fondo inicial."""
        self._movimiento(SentidoMovimiento.ENTRADA, 'USD', Decimal('1000'), tipo=TipoMovimiento.APERTURA)
        self._movimiento(SentidoMovimiento.ENTRADA, 'PYG', Decimal('5000000'), tipo=TipoMovimiento.APERTURA)
        saldo = saldo_registrado(self.turno)
        self.assertEqual(saldo['USD'], Decimal('1000'))
        self.assertEqual(saldo['PYG'], Decimal('5000000'))
        self.assertEqual(saldo['EUR'], Decimal('0'))

    def test_guarani_siempre_presente(self):
        """Aunque la apertura no cargue guaraníes como moneda, PYG aparece para que el cajero lo declare."""
        self.turno.monto_inicial = 0
        self.turno.save()
        self.assertEqual(saldo_inicial(self.turno)['PYG'], Decimal('0'))
        self.assertIn('PYG', saldo_registrado(self.turno))

    def test_es_la_funcion_por_defecto_del_arqueo(self):
        """Sin configuración especial, el arqueo usa este cálculo."""
        from arqueos import integracion
        self.assertEqual(integracion.obtener_saldo_registrado(self.turno)['USD'], Decimal('1000'))
