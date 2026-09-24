from unittest.mock import patch
from django.test import TestCase

# Función hipotética que simula el consumo de una API externa
def obtener_tipo_cambio(moneda):
    # Lógica que eventualmente llamará a la API
    pass

class TipoCambioServiceTestCase(TestCase):

    # 1. MOCKEAR / ARRANGE (Mock directo de la librería requests)
    @patch('requests.get')
    def test_obtener_tipo_cambio_exitoso(self, mock_get):
        """Verifica que el marco de pruebas y el mockeo de la API funcionen correctamente."""
        
        # -------------------------------------------------------------------
        # FASE 1: ARRANGE (Preparar comportamiento del Mock)
        # -------------------------------------------------------------------
        moneda_objetivo = "USD"
        
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "base": "PYG",
            "rates": {"USD": 0.00013}
        }

        # -------------------------------------------------------------------
        # FASE 2: ACT (Simulación de consumo utilizando el mock)
        # -------------------------------------------------------------------
        response = mock_get(f"https://api.exchangerate.host/latest?base=PYG")
        data = response.json()
        resultado = data["rates"].get(moneda_objetivo)

        # -------------------------------------------------------------------
        # FASE 3: ASSERT (Verificaciones)
        # -------------------------------------------------------------------
        self.assertEqual(response.status_code, 200)
        self.assertEqual(resultado, 0.00013)
        mock_get.assert_called_once()