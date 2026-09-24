"""
Módulo de pruebas unitarias e integración para las vistas del módulo Cotizaciones.

Evalúa las vistas públicas ver_cotizaciones (HTML) y api_cotizaciones (JSON),
verificando la correcta integración con las entidades Moneda y TasaDeCambio de operaciones.
"""

from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
from operaciones.models import Moneda, TasaDeCambio


class CotizacionesViewsTestCase(TestCase):
    """Pruebas de controladores y APIs del módulo Cotizaciones."""

    def setUp(self):
        """Inicialización del cliente HTTP y datos de divisas/tasas de cambio."""
        self.client = Client()

        # Moneda habilitada con tasa asignada
        self.moneda_usd = Moneda.objects.create(
            codigo="USD",
            nombre="Dólar Estadounidense",
            habilitada=True
        )
        self.tasa_usd = TasaDeCambio.objects.create(
            moneda=self.moneda_usd,
            tasa_base=Decimal("7500.0000"),
            margen_compra=Decimal("100.0000"),
            margen_venta=Decimal("150.0000")
        )

        # Moneda habilitada sin tasa cargada
        self.moneda_eur = Moneda.objects.create(
            codigo="EUR",
            nombre="Euro",
            habilitada=True
        )

        # Moneda inhabilitada (no debe figurar en las cotizaciones)
        self.moneda_ars = Moneda.objects.create(
            codigo="ARS",
            nombre="Peso Argentino",
            habilitada=False
        )

    def test_ver_cotizaciones_vista_html(self):
        """Verifica el renderizado de la plantilla HTML y los datos en el contexto."""
        response = self.client.get(reverse('ver_cotizaciones'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cotizaciones/lista.html')
        self.assertIn('cotizaciones', response.context)

        cotizaciones = response.context['cotizaciones']
        # Debe incluir solo las 2 monedas habilitadas (USD y EUR)
        self.assertEqual(len(cotizaciones), 2)

        cot_dict = {item['moneda']: item for item in cotizaciones}

        # USD con tasa calculada (Compra: 7500-100=7400, Venta: 7500+150=7650)
        self.assertEqual(cot_dict['USD']['precio_compra'], Decimal("7400.0000"))
        self.assertEqual(cot_dict['USD']['precio_venta'], Decimal("7650.0000"))

        # EUR sin tasa asignada (devuelve "0")
        self.assertEqual(cot_dict['EUR']['precio_compra'], "0")
        self.assertEqual(cot_dict['EUR']['precio_venta'], "0")

        # ARS no debe estar en la lista
        self.assertNotIn('ARS', cot_dict)

    def test_api_cotizaciones_endpoint_json(self):
        """Verifica la respuesta JSON del endpoint api_cotizaciones."""
        response = self.client.get(reverse('api_cotizaciones'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

        json_data = response.json()
        self.assertIn('cotizaciones', json_data)

        lista_cotizaciones = json_data['cotizaciones']
        self.assertEqual(len(lista_cotizaciones), 2)

        cot_dict = {item['moneda']: item for item in lista_cotizaciones}

        self.assertEqual(cot_dict['USD']['compra'], "7400.0000")
        self.assertEqual(cot_dict['USD']['venta'], "7650.0000")
        self.assertEqual(cot_dict['EUR']['compra'], "0")
        self.assertEqual(cot_dict['EUR']['venta'], "0")
        self.assertNotIn('ARS', cot_dict)