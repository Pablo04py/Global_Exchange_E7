"""
Pruebas de los modelos de arqueo (SCRUM-40).

Evalúa la representación textual, la inmutabilidad de los registros de
auditoría y la unicidad de la moneda dentro de un arqueo.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from arqueos.models import ArqueoCaja, DetalleArqueo
from .apoyo import Usuario


class ArqueoModelTestCase(TestCase):
    """Pruebas de ArqueoCaja y DetalleArqueo."""

    def setUp(self):
        """Crea un arqueo con un detalle en USD."""
        self.cajero = Usuario.objects.create_user(username='cajero1', roles=['Cajero'])
        self.arqueo = ArqueoCaja.objects.create(
            caja_id='1', caja_nombre='Caja 1', sucursal_nombre='Casa Central', cajero=self.cajero,
            fecha_cierre=timezone.make_aware(timezone.datetime(2026, 10, 8, 18, 30)),
        )
        self.detalle = DetalleArqueo.objects.create(
            arqueo=self.arqueo, moneda='USD', saldo_registrado=Decimal('900'), saldo_declarado=Decimal('880'),
            diferencia=Decimal('-20'), resultado=DetalleArqueo.Resultado.FALTANTE,
        )

    def test_str(self):
        """Verifica la representación textual del arqueo y del detalle."""
        self.assertEqual(str(self.arqueo), 'Arqueo Caja 1 - 08/10/2026 18:30')
        self.assertEqual(str(self.detalle), 'USD: Faltante (-20)')

    def test_arqueo_no_se_puede_modificar(self):
        """Un arqueo ya registrado no se puede volver a guardar con cambios."""
        self.arqueo.caja_nombre = 'Otra'
        with self.assertRaises(ValidationError):
            self.arqueo.save()

    def test_detalle_no_se_puede_modificar(self):
        """Un detalle ya registrado no se puede volver a guardar con cambios."""
        self.detalle.saldo_declarado = Decimal('900')
        with self.assertRaises(ValidationError):
            self.detalle.save()
        self.detalle.refresh_from_db()
        self.assertEqual(self.detalle.saldo_declarado, Decimal('880'))

    def test_una_fila_por_moneda(self):
        """No puede haber dos detalles de la misma moneda en un arqueo."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            DetalleArqueo.objects.create(
                arqueo=self.arqueo, moneda='USD', saldo_registrado=1, saldo_declarado=1,
                diferencia=0, resultado=DetalleArqueo.Resultado.CUADRA,
            )

    def test_tiene_discrepancias(self):
        """Indica discrepancia si algún detalle no cuadra."""
        self.assertTrue(self.arqueo.tiene_discrepancias)
        sin_diferencias = ArqueoCaja.objects.create(caja_id='2', caja_nombre='Caja 2', cajero=self.cajero)
        DetalleArqueo.objects.create(
            arqueo=sin_diferencias, moneda='PYG', saldo_registrado=10, saldo_declarado=10,
            diferencia=0, resultado=DetalleArqueo.Resultado.CUADRA,
        )
        self.assertFalse(sin_diferencias.tiene_discrepancias)
