"""
Pruebas de la lógica de negocio del cierre de caja (SCRUM-40).

Evalúa el cálculo automático de la diferencia, el registro formal del
sobrante/faltante por moneda y el bloqueo de la caja.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase, override_settings

from arqueos.models import ArqueoCaja, DetalleArqueo
from arqueos.services import calcular_resultado, registrar_cierre
from .apoyo import CONFIG_SUSTITUTA, CajaDePruebaMixin

Resultado = DetalleArqueo.Resultado


class CalcularResultadoTestCase(SimpleTestCase):
    """Pruebas del cálculo de la diferencia (no usan base de datos)."""

    def test_cuadra(self):
        """Declarado igual al registrado: diferencia cero y CUADRA."""
        self.assertEqual(calcular_resultado(Decimal('900'), Decimal('900')), (Decimal('0'), Resultado.CUADRA))

    def test_sobrante(self):
        """Declarado mayor al registrado: diferencia positiva y SOBRANTE."""
        self.assertEqual(calcular_resultado(Decimal('900'), Decimal('950')), (Decimal('50'), Resultado.SOBRANTE))

    def test_faltante(self):
        """Declarado menor al registrado: diferencia negativa y FALTANTE."""
        self.assertEqual(calcular_resultado(Decimal('900'), Decimal('880')), (Decimal('-20'), Resultado.FALTANTE))

    def test_centavos(self):
        """La comparación es exacta con decimales."""
        self.assertEqual(
            calcular_resultado(Decimal('100.50'), Decimal('100.49')), (Decimal('-0.01'), Resultado.FALTANTE)
        )


@override_settings(**CONFIG_SUSTITUTA)
class RegistrarCierreTestCase(CajaDePruebaMixin, TestCase):
    """Pruebas del registro del cierre con la integración configurada."""

    def test_registra_arqueo_por_moneda(self):
        """Guarda un detalle por moneda con registrado, declarado, diferencia y resultado."""
        arqueo = registrar_cierre(self.cajero, {'PYG': Decimal('5740000'), 'USD': Decimal('880')})

        pyg = arqueo.detalles.get(moneda='PYG')
        usd = arqueo.detalles.get(moneda='USD')
        self.assertEqual((pyg.saldo_registrado, pyg.saldo_declarado, pyg.diferencia, pyg.resultado),
                         (Decimal('5740000'), Decimal('5740000'), Decimal('0'), Resultado.CUADRA))
        self.assertEqual((usd.saldo_registrado, usd.saldo_declarado, usd.diferencia, usd.resultado),
                         (Decimal('900'), Decimal('880'), Decimal('-20'), Resultado.FALTANTE))
        self.assertTrue(arqueo.tiene_discrepancias)

    def test_guarda_la_foto_de_la_caja_y_el_cajero(self):
        """El arqueo conserva el identificador, nombre y sucursal de la caja y el cajero."""
        arqueo = registrar_cierre(self.cajero, {'PYG': 5740000, 'USD': 900})
        self.assertEqual(arqueo.caja_id, str(self.caja.pk))
        self.assertIn('Caja 1', arqueo.caja_nombre)
        self.assertEqual(arqueo.sucursal_nombre, 'Casa Central')
        self.assertEqual(arqueo.cajero, self.cajero)
        self.assertFalse(arqueo.tiene_discrepancias)

    def test_bloquea_la_caja(self):
        """Después del cierre la caja queda en el estado de bloqueo configurado."""
        registrar_cierre(self.cajero, {'PYG': 5740000, 'USD': 900})
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.tipo, 'BLOQUEADA')

    def test_no_se_puede_cerrar_dos_veces(self):
        """Una caja ya cerrada (bloqueada) no admite un segundo cierre."""
        registrar_cierre(self.cajero, {'PYG': 5740000, 'USD': 900})
        with self.assertRaises(ValidationError):
            registrar_cierre(self.cajero, {'PYG': 5740000, 'USD': 900})
        self.assertEqual(ArqueoCaja.objects.count(), 1)

    def test_sin_caja_abierta(self):
        """Un cajero sin caja abierta asignada no puede cerrar."""
        with self.assertRaises(ValidationError):
            registrar_cierre(self.otro_cajero, {'PYG': 1, 'USD': 1})
        self.assertEqual(ArqueoCaja.objects.count(), 0)

    def test_monedas_incompletas_no_registran_nada(self):
        """Si falta una moneda se rechaza el cierre y no queda nada a medias (ni arqueo ni bloqueo)."""
        with self.assertRaises(ValidationError):
            registrar_cierre(self.cajero, {'PYG': 5740000})
        self.assertEqual(ArqueoCaja.objects.count(), 0)
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.tipo, 'EFECTIVO')
