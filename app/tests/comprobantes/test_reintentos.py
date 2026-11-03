"""Pruebas de la cola y los reintentos ante caída del SMTP o de Factura Segura (SCRUM-23, criterio 2)."""

from datetime import timedelta
from io import StringIO
from smtplib import SMTPServerDisconnected
from unittest.mock import patch

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from comprobantes.models import EnvioComprobante
from comprobantes.services import encolar_envio, intentar_envio, procesar_pendientes
from facturacion.services.factura_segura import FacturaSeguraError

from .apoyo import KUDE_MOCK, ComprobantesDatosMixin

DESCARGAR_KUDE = 'comprobantes.services.FacturaSeguraService.descargar_kude'
SMTP_CAIDO = patch('comprobantes.services.EmailMessage.send', side_effect=SMTPServerDisconnected('SMTP caído'))


@override_settings(EMAIL_REINTENTO_MINUTOS=5, EMAIL_REINTENTO_VENTANA_MINUTOS=60)
@patch(DESCARGAR_KUDE, return_value=KUDE_MOCK)
class ReintentosTests(ComprobantesDatosMixin, TestCase):
    """Si el SMTP o Factura Segura fallan, el envío queda encolado y se reintenta durante 1 hora."""

    def encolar_y_fallar(self):
        """Encola el envío de una factura aprobada y hace un primer intento con el SMTP caído."""
        envio = encolar_envio(self.crear_factura())
        with SMTP_CAIDO, self.assertLogs('comprobantes.services', level='WARNING'):
            intentar_envio(envio, ahora=envio.fecha_creacion)
        return envio

    def test_smtp_caido_deja_el_envio_pendiente(self, _kude):
        envio = self.encolar_y_fallar()

        envio.refresh_from_db()
        self.assertEqual(envio.estado, EnvioComprobante.Estado.PENDIENTE)
        self.assertEqual(envio.intentos, 1)
        self.assertIn('SMTP caído', envio.ultimo_error)
        self.assertEqual(envio.proximo_intento - envio.fecha_creacion, timedelta(minutes=5))

    def test_falla_al_descargar_el_kude_tambien_se_reintenta(self, mock_kude):
        envio = encolar_envio(self.crear_factura())
        mock_kude.side_effect = FacturaSeguraError('Factura Segura no respondió')
        with self.assertLogs('comprobantes.services', level='WARNING'):
            procesar_pendientes(ahora=envio.fecha_creacion)
        envio.refresh_from_db()
        self.assertEqual(envio.estado, EnvioComprobante.Estado.PENDIENTE)
        self.assertIn('Factura Segura no respondió', envio.ultimo_error)

        mock_kude.side_effect = None
        procesar_pendientes(ahora=envio.proximo_intento)
        envio.refresh_from_db()
        self.assertEqual(envio.estado, EnvioComprobante.Estado.ENVIADO)
        self.assertEqual(len(mail.outbox), 1)

    def test_no_reintenta_antes_del_proximo_intento(self, _kude):
        envio = self.encolar_y_fallar()
        resumen = procesar_pendientes(ahora=envio.proximo_intento - timedelta(seconds=1))
        self.assertEqual(resumen['procesados'], 0)

    def test_reintento_exitoso_cuando_el_smtp_vuelve(self, _kude):
        envio = self.encolar_y_fallar()

        resumen = procesar_pendientes(ahora=envio.proximo_intento)

        self.assertEqual(resumen, {'procesados': 1, 'enviados': 1, 'fallidos': 0})
        envio.refresh_from_db()
        self.assertEqual(envio.estado, EnvioComprobante.Estado.ENVIADO)
        self.assertEqual(envio.intentos, 2)
        self.assertEqual(envio.ultimo_error, '')
        self.assertEqual(len(mail.outbox), 1)

    def test_el_ultimo_reintento_no_pasa_del_fin_de_la_ventana(self, _kude):
        envio = self.encolar_y_fallar()
        with SMTP_CAIDO, self.assertLogs('comprobantes.services', level='WARNING'):
            intentar_envio(envio, ahora=envio.fecha_creacion + timedelta(minutes=58))
        self.assertEqual(envio.estado, EnvioComprobante.Estado.PENDIENTE)
        self.assertEqual(envio.proximo_intento, envio.fecha_creacion + timedelta(minutes=60))

    def test_pasada_la_hora_queda_fallido(self, _kude):
        envio = self.encolar_y_fallar()
        with SMTP_CAIDO, self.assertLogs('comprobantes.services', level='ERROR'):
            resumen = procesar_pendientes(ahora=envio.fecha_creacion + timedelta(minutes=60))

        self.assertEqual(resumen['fallidos'], 1)
        envio.refresh_from_db()
        self.assertEqual(envio.estado, EnvioComprobante.Estado.FALLIDO)
        # Un envío FALLIDO ya no se vuelve a intentar.
        self.assertEqual(procesar_pendientes(ahora=timezone.now() + timedelta(days=1))['procesados'], 0)

    def test_error_no_reintentable_marca_fallido_enseguida(self, mock_kude):
        mock_kude.side_effect = ValueError('respuesta inesperada')
        envio = encolar_envio(self.crear_factura())
        with self.assertLogs('comprobantes.services', level='ERROR'):
            procesar_pendientes(ahora=envio.fecha_creacion)
        envio.refresh_from_db()
        self.assertEqual(envio.estado, EnvioComprobante.Estado.FALLIDO)
        self.assertIn('respuesta inesperada', envio.ultimo_error)

    def test_comando_procesar_envios_manda_los_pendientes(self, _kude):
        envio = self.encolar_y_fallar()
        EnvioComprobante.objects.filter(pk=envio.pk).update(proximo_intento=timezone.now() - timedelta(minutes=1))

        salida = StringIO()
        call_command('procesar_envios', stdout=salida)

        envio.refresh_from_db()
        self.assertEqual(envio.estado, EnvioComprobante.Estado.ENVIADO)
        self.assertIn('enviados: 1', salida.getvalue())
