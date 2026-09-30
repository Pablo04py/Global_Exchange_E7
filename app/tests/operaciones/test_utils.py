"""
Pruebas unitarias de las funciones auxiliares de operaciones.

Evalúa la detección del dispositivo a partir del User-Agent (detectar_dispositivo).
"""

from django.test import SimpleTestCase, RequestFactory

from operaciones.models import Transaccion
from operaciones.utils import detectar_dispositivo

UA_IPHONE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")
UA_IPAD = ("Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
           "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")
UA_ANDROID = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36")
UA_WINDOWS = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
UA_MAC = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 "
          "(KHTML, like Gecko) Version/17.5 Safari/605.1.15")
UA_LINUX = "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0"


class DetectarDispositivoTestCase(SimpleTestCase):
    """Pruebas de detectar_dispositivo."""

    def setUp(self):
        """Crea la fábrica de peticiones."""
        self.factory = RequestFactory()

    def _detectar(self, user_agent):
        """Ejecuta la detección para una petición con el User-Agent indicado."""
        return detectar_dispositivo(self.factory.get('/', HTTP_USER_AGENT=user_agent))

    def test_iphone(self):
        """Un iPhone no debe confundirse con Mac (su User-Agent incluye 'Mac OS X')."""
        self.assertEqual(self._detectar(UA_IPHONE), Transaccion.Dispositivo.IPHONE)

    def test_ipad(self):
        """Verifica la detección de iPad."""
        self.assertEqual(self._detectar(UA_IPAD), Transaccion.Dispositivo.IPAD)

    def test_android(self):
        """Un Android no debe confundirse con Linux (su User-Agent incluye 'Linux')."""
        self.assertEqual(self._detectar(UA_ANDROID), Transaccion.Dispositivo.ANDROID)

    def test_windows(self):
        """Verifica la detección de PC con Windows."""
        self.assertEqual(self._detectar(UA_WINDOWS), Transaccion.Dispositivo.WINDOWS)

    def test_mac(self):
        """Verifica la detección de Mac."""
        self.assertEqual(self._detectar(UA_MAC), Transaccion.Dispositivo.MAC)

    def test_linux(self):
        """Verifica la detección de PC con Linux."""
        self.assertEqual(self._detectar(UA_LINUX), Transaccion.Dispositivo.LINUX)

    def test_user_agent_desconocido(self):
        """Un User-Agent no reconocido devuelve OTRO."""
        self.assertEqual(self._detectar("curl/8.5.0"), Transaccion.Dispositivo.OTRO)

    def test_sin_user_agent(self):
        """Una petición sin cabecera User-Agent devuelve OTRO."""
        self.assertEqual(detectar_dispositivo(self.factory.get('/')), Transaccion.Dispositivo.OTRO)
