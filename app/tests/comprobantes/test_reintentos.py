"""Pruebas de la cola y los reintentos ante caída del SMTP (SCRUM-23, criterio 2)."""

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
from operaciones.models import Transaccion
from operaciones.services import cambiar_estado_transaccion

from .apoyo import ComprobantesDatosMixin

SMTP_CAIDO = patch('comprobantes.services.EmailMessage.send', side_effect=SMTPServerDisconnected('SMTP caído'))


@override_settings(EMAIL_REINTENTO_MINUTOS=5, EMAIL_REINTENTO_VENTANA_MINUTOS=60)
class ReintentosTests(ComprobantesDatosMixin, TestCase):
    """Si el SMTP falla, el envío queda encolado y se reintenta durante 1 hora."""

    def encolar_con_smtp_caido(self):
        """Paga una transacción con el SMTP caído y devuelve el envío encolado."""
        tx = self.crear_pendiente()
        with SMTP_CAIDO, self.captureOnCommitCallbacks(execute=True):
            cambiar_estado_transaccion(tx, Transaccion.Estado.PAGADA, self.cajero)
        return EnvioComprobante.objects.get(transaccion=tx)

    def test_smtp_caido_deja_el_envio_pendiente_sin_afectar_el_pago(self):
        envio = self.encolar_con_smtp_caido()

        self.assertEqual(envio.estado, EnvioComprobante.Estado.PENDIENTE)
        self.assertEqual(envio.intentos, 1)
        self.assertIn('SMTP caído', envio.ultimo_error)
        self.assertEqual(envio.proximo_intento - envio.fecha_creacion, timedelta(minutes=5))
        envio.transaccion.refresh_from_db()
        self.assertEqual(envio.transaccion.estado, Transaccion.Estado.PAGADA)

    def test_no_reintenta_antes_del_proximo_intento(self):
        envio = self.encolar_con_smtp_caido()
        resumen = procesar_pendientes(ahora=envio.proximo_intento - timedelta(seconds=1))
        self.assertEqual(resumen['procesados'], 0)

    def test_reintento_exitoso_cuando_el_smtp_vuelve(self):
        envio = self.encolar_con_smtp_caido()

        resumen = procesar_pendientes(ahora=envio.proximo_intento)

        self.assertEqual(resumen, {'procesados': 1, 'enviados': 1, 'fallidos': 0})
        envio.refresh_from_db()
        self.assertEqual(envio.estado, EnvioComprobante.Estado.ENVIADO)
        self.assertEqual(envio.intentos, 2)
        self.assertEqual(envio.ultimo_error, '')
        self.assertEqual(len(mail.outbox), 1)

    def test_el_ultimo_reintento_no_pasa_del_fin_de_la_ventana(self):
        envio = self.encolar_con_smtp_caido()
        with SMTP_CAIDO:
            intentar_envio(envio, ahora=envio.fecha_creacion + timedelta(minutes=58))
        self.assertEqual(envio.estado, EnvioComprobante.Estado.PENDIENTE)
        self.assertEqual(envio.proximo_intento, envio.fecha_creacion + timedelta(minutes=60))

    def test_pasada_la_hora_queda_fallido(self):
        envio = self.encolar_con_smtp_caido()
        with SMTP_CAIDO, self.assertLogs('comprobantes.services', level='ERROR'):
            resumen = procesar_pendientes(ahora=envio.fecha_creacion + timedelta(minutes=60))

        self.assertEqual(resumen['fallidos'], 1)
        envio.refresh_from_db()
        self.assertEqual(envio.estado, EnvioComprobante.Estado.FALLIDO)
        # Un envío FALLIDO ya no se vuelve a intentar.
        self.assertEqual(procesar_pendientes(ahora=timezone.now() + timedelta(days=1))['procesados'], 0)

    def test_error_que_no_es_de_smtp_marca_fallido_sin_reintentar(self):
        tx = self.crear_pendiente(estado=Transaccion.Estado.PAGADA)
        with patch('comprobantes.services.generar_pdf_comprobante', side_effect=RuntimeError('PDF roto')), \
                self.assertLogs('comprobantes.services', level='ERROR'):
            envio = encolar_envio(tx)
        self.assertEqual(envio.estado, EnvioComprobante.Estado.FALLIDO)
        self.assertIn('PDF roto', envio.ultimo_error)

    def test_comando_procesar_envios_reintenta_los_pendientes(self):
        envio = self.encolar_con_smtp_caido()
        EnvioComprobante.objects.filter(pk=envio.pk).update(proximo_intento=timezone.now() - timedelta(minutes=1))

        salida = StringIO()
        call_command('procesar_envios', stdout=salida)

        envio.refresh_from_db()
        self.assertEqual(envio.estado, EnvioComprobante.Estado.ENVIADO)
        self.assertIn('enviados: 1', salida.getvalue())
