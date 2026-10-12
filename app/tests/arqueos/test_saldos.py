"""
Pruebas del saldo registrado del arqueo (`arqueos.saldos`).

Usa el libro mayor de movimientos (`MovimientoCaja`) para calcular
el efectivo actual de la sesión.
"""

from decimal import Decimal

from django.test import TestCase

from arqueos.saldos import saldo_registrado
from caja.models import MovimientoCaja, SentidoMovimiento, TipoMovimiento
from .apoyo import CajaDePruebaMixin


class SaldoRegistradoTestCase(CajaDePruebaMixin, TestCase):
    """Pruebas del cálculo del saldo registrado mediante MovimientoCaja."""

    def _movimiento(self, sentido, moneda, monto, tipo=TipoMovimiento.OPERACION):
        """Registra un movimiento de efectivo en el turno."""
        MovimientoCaja.objects.create(sesion=self.turno, tipo=tipo, sentido=sentido, moneda=moneda, monto=monto)

    def test_sin_operaciones_es_el_movimiento_inicial(self):
        """Si solo hay apertura, el saldo registrado es el fondo ingresado."""
        self.assertEqual(saldo_registrado(self.turno)['PYG'], Decimal('5000000'))

    def test_suma_entradas_y_resta_salidas(self):
        """Una operación de cambio descuenta y acumula correctamente en el saldo."""
        self._movimiento(SentidoMovimiento.ENTRADA, 'USD', Decimal('100'))
        self._movimiento(SentidoMovimiento.SALIDA, 'PYG', Decimal('740000'))
        saldo = saldo_registrado(self.turno)
        self.assertEqual(saldo['USD'], Decimal('100'))
        self.assertEqual(saldo['PYG'], Decimal('4260000'))

    def test_guarani_siempre_presente(self):
        """PYG aparece en los saldos registrados para que el cajero lo declare."""
        self.assertIn('PYG', saldo_registrado(self.turno))

    def test_es_la_funcion_por_defecto_del_arqueo(self):
        """Sin configuración especial, el arqueo usa este cálculo dinámico."""
        from arqueos import integracion
        self.assertEqual(integracion.obtener_saldo_registrado(self.turno)['PYG'], Decimal('5000000'))