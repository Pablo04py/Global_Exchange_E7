"""
Módulo de pruebas unitarias para los modelos del módulo Cotizaciones (cotizaciones/models.py).
"""

from django.test import TestCase
from decimal import Decimal
from cotizaciones.models import Cotizacion


class CotizacionModelTestCase(TestCase):
    """Pruebas unitarias para la entidad Cotizacion."""

    def test_creacion_cotizacion_y_str(self):
        """Verifica la creación y representación en texto (__str__) de una cotización."""
        cotizacion = Cotizacion.objects.create(
            moneda="USD",
            precio_compra=Decimal("7400.00"),
            precio_venta=Decimal("7650.00")
        )

        self.assertEqual(cotizacion.moneda, "USD")
        self.assertEqual(cotizacion.precio_compra, Decimal("7400.00"))
        self.assertEqual(cotizacion.precio_venta, Decimal("7650.00"))
        self.assertEqual(str(cotizacion), "USD - C: 7400.00 | V: 7650.00")