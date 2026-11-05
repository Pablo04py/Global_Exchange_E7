"""Pruebas del envío propio de facturas reales por email (SCRUM-23, criterio 1).

Las facturas reales las envía Factura Segura al receptor; el envío propio de
la app para ellas es un respaldo que se activa con `COMPROBANTES_ENVIO_PROPIO_REALES`.
Durante los tests Django usa el backend de email `locmem`: los correos quedan
en `mail.outbox` y nunca se envían de verdad. Factura Segura se simula con `patch`.
"""

from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings

from comprobantes.models import EnvioComprobante
from comprobantes.services import asunto_email, encolar_envio, procesar_pendientes
from facturacion.models import FacturaElectronica
from facturacion.services.emision import sincronizar_estado_sifen
from operaciones.models import Transaccion
from operaciones.services import cambiar_estado_transaccion

from .apoyo import KUDE_MOCK, XML_MOCK, ComprobantesDatosMixin

DESCARGAR_KUDE = 'comprobantes.services.FacturaSeguraService.descargar_kude'
URL_TEST = 'https://apitest.facturasegura.com.py'
URL_PRODUCCION = 'https://api.facturasegura.com.py'


@override_settings(COMPROBANTES_ENVIO_PROPIO_REALES=False)
class SinEnvioPropioTests(ComprobantesDatosMixin, TestCase):
    """Por defecto, las facturas reales no generan un segundo correo: lo manda Factura Segura."""

    def test_factura_real_aprobada_no_encola_envio_propio(self):
        self.aprobar(self.crear_factura())
        self.assertFalse(EnvioComprobante.objects.exists())


@override_settings(COMPROBANTES_ENVIO_PROPIO_REALES=True)
class EncoladoTests(ComprobantesDatosMixin, TestCase):
    """Con el respaldo activo, el envío se encola cuando la factura queda `APROBADA` y solo en ese caso."""

    def test_factura_aprobada_encola_un_envio_pendiente(self):
        factura = self.aprobar(self.crear_factura())

        envio = EnvioComprobante.objects.get(factura=factura)
        self.assertEqual(envio.estado, EnvioComprobante.Estado.PENDIENTE)
        self.assertEqual(envio.destinatarios, [self.EMAIL_CLIENTE])
        self.assertEqual(envio.intentos, 0)
        # El correo no sale en el mismo guardado: lo manda el mailer.
        self.assertEqual(len(mail.outbox), 0)

    def test_otros_estados_no_encolan(self):
        for estado in (FacturaElectronica.Estado.EMITIDA, FacturaElectronica.Estado.RECHAZADA,
                       FacturaElectronica.Estado.ERROR):
            with self.subTest(estado=estado), self.captureOnCommitCallbacks(execute=True):
                self.crear_factura(estado=estado)
        self.assertFalse(EnvioComprobante.objects.exists())

    def test_no_encola_si_la_aprobacion_no_llega_a_guardarse(self):
        """Sin commit (por ejemplo, si hay rollback) no se encola nada."""
        factura = self.crear_factura()
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            factura.estado = FacturaElectronica.Estado.APROBADA
            factura.save()
        self.assertEqual(len(callbacks), 1)
        self.assertFalse(EnvioComprobante.objects.exists())

    def test_guardar_dos_veces_la_factura_aprobada_no_duplica_el_envio(self):
        factura = self.aprobar(self.crear_factura())
        self.aprobar(factura)
        self.assertEqual(EnvioComprobante.objects.filter(factura=factura).count(), 1)

    @override_settings(FACTURACION_EMISION_AUTOMATICA=False, COMPROBANTES_SIMULAR_FACTURA=False)
    def test_pagar_la_transaccion_no_envia_correo(self):
        """Sin modo simulación, el correo depende de la factura aprobada, no del pago."""
        tx = self.crear_pendiente()
        with self.captureOnCommitCallbacks(execute=True):
            cambiar_estado_transaccion(tx, Transaccion.Estado.PAGADA, self.cajero)
        self.assertFalse(EnvioComprobante.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_cliente_sin_emails_no_encola(self):
        self.usuario_a.email = ''
        self.usuario_a.save(update_fields=['email'])
        with self.assertLogs('comprobantes.services', level='WARNING'):
            self.aprobar(self.crear_factura())
        self.assertFalse(EnvioComprobante.objects.exists())

    def test_en_caja_lo_recibe_el_cliente_y_no_el_cajero(self):
        tx = self.crear_pendiente(usuario=self.cajero, canal=Transaccion.Canal.CAJA,
                                  estado=Transaccion.Estado.PAGADA)
        factura = self.aprobar(self.crear_factura(tx))
        self.assertEqual(factura.envio_email.destinatarios, [self.EMAIL_CLIENTE])

    @patch('facturacion.services.emision.FacturaSeguraService.get_estado_sifen')
    def test_la_aprobacion_desde_sifen_encola_el_envio(self, mock_estado):
        """Integración con SCRUM-56: `sincronizar_estado_sifen` aprueba la factura y se encola el envío."""
        mock_estado.return_value = {
            'code': 0, 'description': 'OK', 'operation_info': {'id': 'mock-sifen'},
            'results': [{'estado_sifen': 'Aprobado', 'desc_sifen': '0260 - Aprobado', 'error_sifen': ''}],
        }
        factura = self.crear_factura()
        with self.captureOnCommitCallbacks(execute=True):
            sincronizar_estado_sifen(factura)
        self.assertTrue(EnvioComprobante.objects.filter(factura=factura).exists())


@override_settings(COMPROBANTES_ENVIO_PROPIO_REALES=True, FACTURA_SEGURA_BASE_URL=URL_TEST)
class EnvioTests(ComprobantesDatosMixin, TestCase):
    """El mailer manda el XML y el KuDE con el mismo formato que el correo de Factura Segura."""

    @patch(DESCARGAR_KUDE, return_value=KUDE_MOCK)
    def test_envia_el_xml_y_el_kude_al_cliente_con_el_formato_de_factura_segura(self, mock_kude):
        factura = self.aprobar(self.crear_factura())

        resumen = procesar_pendientes()

        self.assertEqual(resumen, {'procesados': 1, 'enviados': 1, 'fallidos': 0})
        mock_kude.assert_called_once_with(ruc_emisor='2595733', cdc=factura.cdc)
        self.mock_descargar_xml.assert_called_once_with(ruc_emisor='2595733', cdc=factura.cdc)
        correo = mail.outbox[0]
        self.assertEqual(correo.to, [self.EMAIL_CLIENTE])
        self.assertEqual(correo.subject, 'TEST KuDE Factura electrónica 001-003-0000217 - DE generado en '
                                         'ambiente de prueba - sin valor comercial ni fiscal')
        for texto in ('Estimado/a cliente Ana Pérez:',
                      'Adjunto encontrará el KuDE y el XML de la Factura electrónica 001-003-0000217',
                      f'CDC: {factura.cdc}', 'Cordialmente,', 'RUC:2595733-3', '#FacturaSegura'):
            self.assertIn(texto, correo.body)

        (nombre_xml, xml, tipo_xml), (nombre_pdf, pdf, tipo_pdf) = correo.attachments
        self.assertEqual((nombre_xml, xml, tipo_xml), (f'{factura.cdc}.xml', XML_MOCK, 'application/xml'))
        self.assertRegex(nombre_pdf, rf'^{factura.cdc}_\d{{8}}_\d{{6}}\.pdf$')
        self.assertEqual((pdf, tipo_pdf), (KUDE_MOCK, 'application/pdf'))

        envio = factura.envio_email
        envio.refresh_from_db()
        self.assertEqual(envio.estado, EnvioComprobante.Estado.ENVIADO)
        self.assertEqual(envio.intentos, 1)
        self.assertIsNotNone(envio.fecha_envio)

    @override_settings(FACTURA_SEGURA_BASE_URL=URL_PRODUCCION)
    def test_en_produccion_el_asunto_no_lleva_la_leyenda_de_prueba(self):
        factura = self.crear_factura()
        self.assertEqual(asunto_email(factura), 'KuDE Factura electrónica 001-003-0000217')

    @patch(DESCARGAR_KUDE, return_value=KUDE_MOCK)
    def test_un_envio_ya_enviado_no_se_vuelve_a_mandar(self, mock_kude):
        factura = self.aprobar(self.crear_factura())
        procesar_pendientes()
        encolar_envio(factura)
        self.assertEqual(procesar_pendientes()['procesados'], 0)
        self.assertEqual(len(mail.outbox), 1)
