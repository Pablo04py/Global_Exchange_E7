"""
Pruebas del saldo registrado del arqueo (`arqueos.saldos`).

El saldo se calcula desde el libro mayor de movimientos de la caja
(`MovimientoCaja`): la apertura (SCRUM-37) registra el fondo inicial como
movimientos `APERTURA` y cada operación (SCRUM-39) suma o resta efectivo.
"""

from decimal import Decimal

from django.test import TestCase

from arqueos import integracion
from arqueos.saldos import saldo_registrado
from caja.models import MovimientoCaja, SentidoMovimiento, TipoMovimiento
from .apoyo import CajaDePruebaMixin


class SaldoRegistradoTestCase(CajaDePruebaMixin, TestCase):
    """Pruebas del cálculo: fondo de apertura + entradas - salidas, por moneda."""

    def setUp(self):
        """Registra la apertura del turno: 5.000.000 PYG y 1.000 USD de fondo inicial."""
        super().setUp()
        self._movimiento(SentidoMovimiento.ENTRADA, 'PYG', Decimal('5000000'), TipoMovimiento.APERTURA)
        self._movimiento(SentidoMovimiento.ENTRADA, 'USD', Decimal('1000'), TipoMovimiento.APERTURA)

    def _movimiento(self, sentido, moneda, monto, tipo=TipoMovimiento.OPERACION):
        """Registra un movimiento de efectivo en el turno."""
        MovimientoCaja.objects.create(sesion=self.turno, tipo=tipo, sentido=sentido, moneda=moneda, monto=monto)

    def test_sin_operaciones_es_el_fondo_de_apertura(self):
        """Si solo hay apertura, el saldo registrado es el fondo inicial de cada moneda."""
        self.assertEqual(saldo_registrado(self.turno), {'PYG': Decimal('5000000'), 'USD': Decimal('1000')})

    def test_suma_entradas_y_resta_salidas(self):
        """Una venta de 100 USD a 7.400: entra la divisa y sale el efectivo en guaraníes."""
        self._movimiento(SentidoMovimiento.ENTRADA, 'USD', Decimal('100'))
        self._movimiento(SentidoMovimiento.SALIDA, 'PYG', Decimal('740000'))
        saldo = saldo_registrado(self.turno)
        self.assertEqual(saldo['USD'], Decimal('1100'))
        self.assertEqual(saldo['PYG'], Decimal('4260000'))

    def test_monedas_del_cierre_son_las_de_la_caja(self):
        """El cierre pide las monedas con movimientos en el turno (las abiertas u operadas)."""
        self._movimiento(SentidoMovimiento.ENTRADA, 'EUR', Decimal('50'))
        self.assertEqual(set(saldo_registrado(self.turno)), {'PYG', 'USD', 'EUR'})

    def test_es_la_funcion_por_defecto_del_arqueo(self):
        """Sin configuración especial, el arqueo usa este cálculo."""
        self.assertEqual(integracion.obtener_saldo_registrado(self.turno)['PYG'], Decimal('5000000'))
