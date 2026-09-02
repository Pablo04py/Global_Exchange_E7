# ==============================================================================
# GUÍA BÁSICA DE PRUEBAS UNITARIAS: PATRÓN AAA Y MOCKS
# ==============================================================================
# En este archivo aprenderás cómo estructurar una prueba unitaria desde cero.
# Toda buena prueba unitaria consta de 3 fases obligatorias:
#
#   1. ARRANGE (Preparar):  Configuras las variables, objetos o respuestas falsas.
#   2. ACT     (Ejecutar):  Llamas al método o función que quieres probar.
#   3. ASSERT  (Verificar): Compruebas que el resultado sea exactamente el esperado.
# ==============================================================================

from unittest.mock import patch
from django.test import TestCase


# ------------------------------------------------------------------------------
# CÓDIGO A PROBAR (Función o Servicio)
# ------------------------------------------------------------------------------
# Esta es la función ficticia que normalmente estaría en tus archivos de servicio.
# Simula una llamada a un servicio web externo (como un proveedor de divisas).
def obtener_tipo_cambio(moneda):
    # En producción aquí se ejecutaría una petición http real a la API externa
    pass


# ------------------------------------------------------------------------------
# CLASE DE PRUEBAS UNITARIAS
# ------------------------------------------------------------------------------
# Para crear pruebas en Django, heredamos de `TestCase`.
# Cada método que empiece con la palabra `test_` será ejecutado por el runner.
class TipoCambioServiceTestCase(TestCase):

    # --------------------------------------------------------------------------
    # USO DE MOCKS (@patch):
    # ¿Por qué mockear?: Un test NUNCA debe hacer peticiones HTTP reales a internet.
    # Usamos `@patch` para reemplazar temporalmente la librería `requests.get` por
    # un objeto simulado (mock) que nosotros controlamos.
    # --------------------------------------------------------------------------
    @patch('requests.get')
    def test_obtener_tipo_cambio_exitoso(self, mock_get):

        # ======================================================================
        # FASE 1: ARRANGE (Preparación del escenario)
        # ======================================================================
        # En esta etapa preparamos los datos de entrada y le indicamos al Mock
        # cómo debe comportarse cuando sea invocado dentro de la prueba.
        
        # 1. Definimos los datos de entrada
        moneda_objetivo = "USD"

        # 2. Le indicamos al mock qué responder (Respuesta simulada de la API)
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "base": "PYG",
            "rates": {"USD": 0.00013}
        }

        # ======================================================================
        # FASE 2: ACT (Ejecución de la acción)
        # ======================================================================
        # En esta etapa ejecutamos el código que estamos probando.
        # Aquí simulamos la llamada llamando al mock configurado previamente.
        
        response = mock_get("https://api.exchangerate.host/latest?base=PYG")
        data = response.json()
        resultado = data["rates"].get(moneda_objetivo)

        # ======================================================================
        # FASE 3: ASSERT (Verificación de resultados)
        # ======================================================================
        # En esta última etapa usamos las afirmaciones (`self.assert*`) para validar
        # que todo haya funcionado según las reglas de negocio planteadas.

        # 1. Verificamos que el código de respuesta HTTP sea 200 (OK)
        self.assertEqual(response.status_code, 200)

        # 2. Verificamos que el valor devuelto sea exactamente la tasa simulada (0.00013)
        self.assertEqual(resultado, 0.00013)

        # 3. Verificamos que la API externa fue consultada exactamente 1 vez (evita llamadas duplicadas)
        mock_get.assert_called_once()