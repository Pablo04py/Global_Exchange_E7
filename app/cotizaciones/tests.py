from django.test import TestCase
from django.urls import reverse
from .models import Cotizacion

class CotizacionTestCase(TestCase):
    """
    Pruebas unitarias para el CRUD de Cotizaciones.
    Evalúa la creación en BD y las respuestas de las vistas.
    """
    
    def setUp(self):
        # Datos de prueba iniciales
        self.cotizacion = Cotizacion.objects.create(
            moneda="USD", 
            precio_compra=7200.50, 
            precio_venta=7300.00
        )
        self.listar_url = reverse('listar_cotizaciones') # Asegúrate de que los names en urls.py coincidan

    def test_creacion_modelo(self):
        """Verifica que el modelo guarde correctamente los datos."""
        cot = Cotizacion.objects.get(moneda="USD")
        self.assertEqual(cot.precio_compra, 7200.50)

    def test_vista_listar_cotizaciones(self):
        """Verifica que la vista de listado devuelva un código HTTP 200 (OK)."""
        response = self.client.get(self.listar_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "USD")