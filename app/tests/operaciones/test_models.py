"""
Módulo de pruebas unitarias para los modelos de Operaciones (operaciones/models.py).

Valida la creación, valores predeterminados, representación en texto (__str__)
y la precisión matemática de los cálculos de precios de compra y venta en TasaDeCambio.
"""

from django.test import TestCase
from decimal import Decimal
from operaciones.models import Moneda, TasaDeCambio


class MonedaModelTestCase(TestCase):
    """Pruebas unitarias para la entidad Moneda."""

    def test_creacion_moneda_exitosa(self):
        """Verifica la persistencia de una divisa y sus valores predeterminados."""
        moneda = Moneda.objects.create(
            codigo="USD",
            nombre="Dólar Estadounidense"
        )

        self.assertEqual(moneda.codigo, "USD")
        self.assertEqual(moneda.nombre, "Dólar Estadounidense")
        self.assertTrue(moneda.habilitada)  # Habilitada por defecto
        self.assertEqual(str(moneda), "USD")

    def test_unicidad_codigo_moneda(self):
        """Verifica que el código ISO 4217 sea único."""
        Moneda.objects.create(codigo="EUR", nombre="Euro")
        
        with self.assertRaises(Exception):
            Moneda.objects.create(codigo="EUR", nombre="Euro Duplicado")


class TasaDeCambioModelTestCase(TestCase):
    """Pruebas unitarias para la entidad TasaDeCambio y sus métodos de cálculo."""

    def setUp(self):
        """Inicialización de moneda base para las pruebas de tasa de cambio."""
        self.moneda = Moneda.objects.create(
            codigo="BRL",
            nombre="Real Brasileño"
        )

    def test_creacion_tasa_y_metodos_de_calculo(self):
        """Verifica la persistencia de la tasa y los resultados de calcular_precio_compra / venta."""
        tasa = TasaDeCambio.objects.create(
            moneda=self.moneda,
            tasa_base=Decimal("1400.0000"),
            margen_compra=Decimal("50.0000"),
            margen_venta=Decimal("80.0000")
        )

        # Precio Compra = TasaBase - MargenCompra (1400 - 50 = 1350)
        self.assertEqual(tasa.calcular_precio_compra(), Decimal("1350.0000"))

        # Precio Venta = TasaBase + MargenVenta (1400 + 80 = 1480)
        self.assertEqual(tasa.calcular_precio_venta(), Decimal("1480.0000"))

        # Verificación del formato __str__
        self.assertIn("BRL @", str(tasa))