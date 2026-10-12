"""
Pruebas de integración del cierre de caja y del detalle del arqueo (SCRUM-40).

El cierre se hace en la pantalla única de apertura y cierre (`caja:apertura_caja`).
Evalúa el acceso, el arqueo ciego, el registro del cierre y el bloqueo de la
caja, el resultado mostrado en la misma pantalla, los avisos cuando no hay
caja o módulo disponible, la ruta histórica `/arqueos/cerrar/` y el acceso al
detalle del arqueo.
"""

from django.test import TestCase, override_settings
from django.urls import reverse

from arqueos.models import ArqueoCaja
from caja.models import EstadoCaja, EstadoSesionCaja
from .apoyo import CONFIG_PRUEBA, CajaDePruebaMixin

URL_CIERRE = reverse('caja:apertura_caja')


@override_settings(ARQUEO_FUNCION_SALDO='no_existe.saldo')
class CierreSinModuloTestCase(CajaDePruebaMixin, TestCase):
    """Cuando la función de saldo registrado (otra historia) todavía no existe."""

    def test_muestra_aviso_de_modulo_no_disponible(self):
        """El cajero con turno abierto ve un aviso en lugar de un error."""
        self.client.force_login(self.cajero)
        response = self.client.get(URL_CIERRE)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'El módulo de caja todavía no está disponible')


@override_settings(**CONFIG_PRUEBA)
class CierreCajaViewTestCase(CajaDePruebaMixin, TestCase):
    """Pruebas de la pantalla de cierre con la integración configurada."""

    def _datos_validos(self):
        """Saldos declarados: PYG cuadra y USD con faltante de 20."""
        return {'saldo_PYG': '5740000', 'saldo_USD': '880'}

    def test_anonimo_no_accede(self):
        """Un usuario no autenticado es enviado al login y no ve el formulario."""
        response = self.client.get(URL_CIERRE)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(reverse('caja:apertura_caja'), response.url.split('?')[0])

    def test_usuario_sin_turno_no_cierra(self):
        """Un usuario sin turno (ej. Administrador) ve el aviso y no puede cerrar."""
        self.client.force_login(self.admin)
        response = self.client.get(URL_CIERRE)
        self.assertContains(response, 'No tenés una caja asignada para abrir')
        self.client.post(URL_CIERRE, self._datos_validos())
        self.assertEqual(ArqueoCaja.objects.count(), 0)

    def test_cajero_sin_caja_abierta(self):
        """Un cajero sin turno abierto ve el aviso correspondiente."""
        self.client.force_login(self.otro_cajero)
        response = self.client.get(URL_CIERRE)
        self.assertContains(response, 'No tenés una caja asignada para abrir')
        self.assertNotContains(response, 'Cerrar caja')

    def test_arqueo_ciego(self):
        """El formulario pide un saldo por moneda sin mostrar el saldo registrado."""
        self.client.force_login(self.cajero)
        response = self.client.get(URL_CIERRE)
        self.assertContains(response, 'name="saldo_PYG"')
        self.assertContains(response, 'name="saldo_USD"')
        for registrado in ['5740000', '5\xa0740\xa0000', '900,00']:
            self.assertNotContains(response, registrado)

    def test_muestra_la_caja_del_turno(self):
        """La pantalla indica qué caja se va a cerrar."""
        self.client.force_login(self.cajero)
        self.assertContains(self.client.get(URL_CIERRE), 'Caja 1 (C1)')

    def test_cierre_registra_arqueo_y_bloquea_la_caja(self):
        """Un cierre válido guarda el arqueo, cierra el turno, bloquea la caja y vuelve a la misma pantalla."""
        self.client.force_login(self.cajero)
        response = self.client.post(URL_CIERRE, self._datos_validos())

        arqueo = ArqueoCaja.objects.get()
        self.assertRedirects(response, f'{URL_CIERRE}?arqueo={arqueo.id}')
        self.assertEqual(arqueo.detalles.get(moneda='USD').resultado, 'FALTANTE')
        self.refrescar()
        self.assertEqual(self.turno.estado, EstadoSesionCaja.CERRADA)
        self.assertEqual(self.caja.estado, EstadoCaja.INACTIVA)

    def test_despues_de_cerrar_no_hay_caja_para_cerrar(self):
        """Tras el cierre, la caja bloqueada ya no aparece para cerrar de nuevo."""
        self.client.force_login(self.cajero)
        self.client.post(URL_CIERRE, self._datos_validos())
        response = self.client.get(URL_CIERRE)
        self.assertContains(response, 'No tenés una caja asignada para abrir')

    def test_resultado_en_la_misma_pantalla(self):
        """Después del cierre, la pantalla de apertura y cierre muestra la comparación."""
        self.client.force_login(self.cajero)
        response = self.client.post(URL_CIERRE, self._datos_validos(), follow=True)
        self.assertEqual(response.context['modo'], 'resultado')
        for texto in ['Resultado del cierre', 'Caja 1 (C1)', 'Cuadra', 'Faltante', '880,00', '900,00', '-20,00']:
            with self.subTest(texto=texto):
                self.assertContains(response, texto)

    def test_resultado_ajeno_no_se_muestra(self):
        """Otro cajero no puede ver un arqueo ajeno con `?arqueo=<id>`; tampoco un id inválido falla."""
        self.client.force_login(self.cajero)
        self.client.post(URL_CIERRE, self._datos_validos())
        arqueo = ArqueoCaja.objects.get()
        self.client.force_login(self.otro_cajero)
        for valor in [arqueo.id, 'no-es-uuid']:
            with self.subTest(valor=valor):
                response = self.client.get(f'{URL_CIERRE}?arqueo={valor}')
                self.assertEqual(response.context['modo'], 'sin_caja')

    def test_ruta_historica_redirige(self):
        """`/arqueos/cerrar/` redirige a la pantalla única de apertura y cierre."""
        self.client.force_login(self.cajero)
        self.assertRedirects(self.client.get(reverse('cerrar_caja')), URL_CIERRE)

    def test_saldo_invalido_no_registra_nada(self):
        """Un saldo negativo o vacío muestra error y no cierra la caja."""
        self.client.force_login(self.cajero)
        for datos in [{'saldo_PYG': '-1', 'saldo_USD': '880'}, {'saldo_PYG': '5740000'}]:
            with self.subTest(datos=datos):
                response = self.client.post(URL_CIERRE, datos)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors)
        self.assertEqual(ArqueoCaja.objects.count(), 0)
        self.refrescar()
        self.assertEqual(self.turno.estado, EstadoSesionCaja.ABIERTA)
        self.assertEqual(self.caja.estado, EstadoCaja.EN_USO)


@override_settings(**CONFIG_PRUEBA)
class DetalleArqueoViewTestCase(CajaDePruebaMixin, TestCase):
    """Pruebas de la pantalla con el resultado del arqueo."""

    def setUp(self):
        """Registra un cierre del cajero 1."""
        super().setUp()
        self.client.force_login(self.cajero)
        self.client.post(URL_CIERRE, {'saldo_PYG': '5740000', 'saldo_USD': '950'})
        self.arqueo = ArqueoCaja.objects.get()
        self.url = reverse('detalle_arqueo', kwargs={'arqueo_id': self.arqueo.id})

    def test_muestra_la_comparacion(self):
        """Después del cierre se ven registrado, declarado, diferencia y resultado."""
        response = self.client.get(self.url)
        for texto in ['Caja 1 (C1)', 'María González', 'Cuadra', 'Sobrante', '950,00', '900,00', '50,00']:
            with self.subTest(texto=texto):
                self.assertContains(response, texto)

    def test_otro_cajero_no_ve_el_arqueo(self):
        """Un cajero no puede ver arqueos de otro cajero (404)."""
        self.client.force_login(self.otro_cajero)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_administrador_ve_cualquier_arqueo(self):
        """El Administrador General puede ver el arqueo de cualquier cajero."""
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_solo_lectura(self):
        """La pantalla del resultado no ofrece formularios para modificar el arqueo."""
        response = self.client.get(self.url)
        self.assertNotContains(response, 'name="saldo_')
