"""
Pruebas de la habilitación de cajas bloqueadas por un cierre (SCRUM-40).

Evalúa que solo el Administrador General pueda habilitar, que solo se listen
y habiliten cajas bloqueadas por un cierre y que la caja habilitada vuelva a
estar disponible para la asignación de SCRUM-36.
"""

from django.contrib.auth.models import Group
from django.contrib.messages import get_messages
from django.test import TestCase, override_settings
from django.urls import reverse

from arqueos.models import ArqueoCaja
from arqueos.services import registrar_cierre
from caja.forms import AsignarCajeroForm
from caja.models import Caja, EstadoCaja
from .apoyo import CONFIG_PRUEBA, CajaDePruebaMixin

URL_LISTA = reverse('cajas_bloqueadas')


def url_habilitar(caja):
    """Devuelve la URL para habilitar la caja."""
    return reverse('habilitar_caja', kwargs={'caja_id': caja.pk})


@override_settings(**CONFIG_PRUEBA)
class HabilitarCajaTestCase(CajaDePruebaMixin, TestCase):
    """Pruebas de la lista de cajas bloqueadas y de la habilitación."""

    def setUp(self):
        """Cierra la caja del cajero (queda bloqueada) y crea otra caja inactiva sin cierre."""
        super().setUp()
        self.arqueo = registrar_cierre(self.cajero, {'PYG': 5740000, 'USD': 880})
        self.inactiva_sin_cierre = Caja.objects.create(nombre='Caja 9', codigo='C9', estado=EstadoCaja.INACTIVA)
        self.client.force_login(self.admin)

    def _mensajes(self, response):
        """Devuelve los textos de los mensajes de la respuesta."""
        return [str(m) for m in get_messages(response.wsgi_request)]

    def test_lista_solo_cajas_bloqueadas_por_cierre(self):
        """Lista la caja cerrada con su último arqueo y no la caja inactiva sin cierre."""
        response = self.client.get(URL_LISTA)
        bloqueadas = response.context['bloqueadas']
        self.assertEqual([item['caja'] for item in bloqueadas], [self.caja])
        self.assertEqual(bloqueadas[0]['ultimo_arqueo'], self.arqueo)
        self.assertContains(response, 'Caja 1 (C1)')
        self.assertNotContains(response, 'Caja 9')

    def test_solo_el_administrador_accede(self):
        """Un cajero recibe 403 en la lista y al intentar habilitar; un anónimo también."""
        self.client.force_login(self.cajero)
        self.assertEqual(self.client.get(URL_LISTA).status_code, 403)
        self.assertEqual(self.client.post(url_habilitar(self.caja)).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(URL_LISTA).status_code, 403)
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.estado, EstadoCaja.INACTIVA)

    def test_habilitar_deja_la_caja_disponible(self):
        """Habilitar pasa la caja a DISPONIBLE, informa el resultado y la quita de la lista."""
        response = self.client.post(url_habilitar(self.caja))
        self.assertRedirects(response, URL_LISTA)
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.estado, EstadoCaja.DISPONIBLE)
        self.assertIn('fue habilitada', self._mensajes(response)[0])
        self.assertEqual(self.client.get(URL_LISTA).context['bloqueadas'], [])

    def test_el_arqueo_no_se_modifica(self):
        """Habilitar la caja no altera el arqueo registrado."""
        self.client.post(url_habilitar(self.caja))
        self.assertEqual(ArqueoCaja.objects.get().detalles.get(moneda='USD').resultado, 'FALTANTE')

    def test_caja_habilitada_vuelve_a_poder_asignarse(self):
        """La caja habilitada aparece de nuevo entre las cajas asignables (SCRUM-36)."""
        self.assertNotIn(self.caja, AsignarCajeroForm().fields['caja'].queryset)
        self.client.post(url_habilitar(self.caja))
        self.assertIn(self.caja, AsignarCajeroForm().fields['caja'].queryset)

    def test_solo_por_post(self):
        """La habilitación no se ejecuta con GET."""
        self.assertEqual(self.client.get(url_habilitar(self.caja)).status_code, 405)
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.estado, EstadoCaja.INACTIVA)

    def test_no_habilita_cajas_no_bloqueadas_por_cierre(self):
        """Una caja inactiva sin cierre o una ya habilitada no se modifica y se informa el error."""
        self.client.post(url_habilitar(self.caja), follow=True)  # sigue la redirección: consume el mensaje
        for caja in [self.inactiva_sin_cierre, self.caja]:
            with self.subTest(caja=caja):
                estado_previo = Caja.objects.get(pk=caja.pk).estado
                response = self.client.post(url_habilitar(caja), follow=True)
                mensajes = [str(m) for m in response.context['messages']]
                self.assertEqual(len(mensajes), 1)
                self.assertIn('no está bloqueada por un cierre', mensajes[0])
                self.assertEqual(Caja.objects.get(pk=caja.pk).estado, estado_previo)

    def test_identificador_invalido(self):
        """Un identificador inexistente o mal formado responde con un mensaje, sin error del servidor."""
        response = self.client.post(reverse('habilitar_caja', kwargs={'caja_id': 'no-es-un-id'}))
        self.assertRedirects(response, URL_LISTA)
        self.assertTrue(self._mensajes(response))

    def test_sin_cajas_bloqueadas(self):
        """Si no hay cajas bloqueadas se muestra el aviso correspondiente."""
        self.client.post(url_habilitar(self.caja))
        self.assertContains(self.client.get(URL_LISTA), 'No hay cajas bloqueadas')

    def _urls_del_menu(self, usuario, rol):
        """Devuelve las URLs del menú del dashboard para un usuario con el rol (grupo de Keycloak) dado."""
        usuario.groups.add(Group.objects.get_or_create(name=rol)[0])
        self.client.force_login(usuario)
        secciones = self.client.get(reverse('dashboard')).context['menu_sections']
        return [item['url'] for seccion in secciones for item in seccion['items']]

    def test_menu_del_administrador_incluye_cajas_bloqueadas(self):
        """El menú del Administrador General tiene el acceso a Cajas Bloqueadas; el del cajero no."""
        self.assertIn(URL_LISTA, self._urls_del_menu(self.admin, 'Administrador General'))
        self.assertNotIn(URL_LISTA, self._urls_del_menu(self.cajero, 'Cajero'))
