"""Pruebas del modo simulación: cada pago genera una factura aprobada y se envía por email (SCRUM-23)."""

from unittest.mock import patch
from xml.etree import ElementTree as ET

from django.core import mail
from django.template.loader import render_to_string
from django.test import TestCase, override_settings

from comprobantes.kude import PLANTILLA, contexto_kude, generar_kude_simulado, generar_xml_simulado
from comprobantes.models import EnvioComprobante
from comprobantes.services import procesar_pendientes
from comprobantes.simulacion import emitir_factura_simulada, es_factura_simulada
from facturacion.models import FacturaElectronica
from operaciones.models import Transaccion
from operaciones.services import cambiar_estado_transaccion

from .apoyo import ComprobantesDatosMixin

DESCARGAR_KUDE = 'comprobantes.services.FacturaSeguraService.descargar_kude'


@override_settings(COMPROBANTES_SIMULAR_FACTURA=True, FACTURACION_EMISION_AUTOMATICA=False)
class SimulacionAlPagarTests(ComprobantesDatosMixin, TestCase):
    """Con el modo simulación activo, pagar genera la factura aprobada y encola el envío."""

    def pagar(self, tx=None, nuevo_estado=Transaccion.Estado.PAGADA):
        """Cambia el estado de la transacción ejecutando los callbacks `on_commit`."""
        tx = tx or self.crear_pendiente()
        with self.captureOnCommitCallbacks(execute=True):
            cambiar_estado_transaccion(tx, nuevo_estado, self.cajero, motivo='test')
        tx.refresh_from_db()
        return tx

    def test_pagar_genera_factura_aprobada_simulada_y_encola_el_envio(self):
        tx = self.pagar()

        factura = FacturaElectronica.objects.get(transaccion=tx)
        self.assertEqual(factura.estado, FacturaElectronica.Estado.APROBADA)
        self.assertEqual(factura.numero_documento, '9000001')
        self.assertTrue(factura.cdc.startswith('SIMULADO'))
        self.assertEqual(len(factura.cdc), 44)
        self.assertIsNotNone(factura.fecha_aprobacion)
        self.assertTrue(es_factura_simulada(factura))
        self.assertTrue(tx.facturada)
        self.assertEqual(factura.envio_email.estado, EnvioComprobante.Estado.PENDIENTE)
        self.assertEqual(factura.envio_email.destinatarios, [self.EMAIL_CLIENTE])
        # La numeración fiscal real no se toca.
        self.configuracion.refresh_from_db()
        self.assertEqual(self.configuracion.siguiente_numero_documento, 216)

    def test_la_serie_simulada_es_correlativa(self):
        primera = self.pagar()
        segunda = self.pagar(self.crear_pendiente(tipo=Transaccion.Tipo.VENTA))
        self.assertEqual(primera.factura.numero_documento, '9000001')
        self.assertEqual(segunda.factura.numero_documento, '9000002')

    @patch(DESCARGAR_KUDE)
    def test_el_mailer_envia_xml_y_kude_simulados_sin_llamar_a_factura_segura(self, mock_kude):
        tx = self.pagar()

        resumen = procesar_pendientes()

        self.assertEqual(resumen['enviados'], 1)
        mock_kude.assert_not_called()
        self.mock_descargar_xml.assert_not_called()
        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertEqual(correo.to, [self.EMAIL_CLIENTE])
        self.assertEqual(correo.subject, 'SIMULACIÓN KuDE Factura electrónica 001-003-9000001 - DE simulado '
                                         'localmente - sin valor comercial ni fiscal')
        self.assertIn('Adjunto encontrará el KuDE y el XML de la Factura electrónica 001-003-9000001', correo.body)
        self.assertIn('simulación', correo.body)
        (nombre_xml, xml, tipo_xml), (nombre_pdf, pdf, tipo_pdf) = correo.attachments
        self.assertEqual((nombre_xml, tipo_xml), (f'{tx.factura.cdc}.xml', 'application/xml'))
        self.assertEqual(ET.fromstring(xml).find('DE').get('Id'), tx.factura.cdc)
        self.assertTrue(nombre_pdf.startswith(tx.factura.cdc) and nombre_pdf.endswith('.pdf'))
        self.assertEqual(tipo_pdf, 'application/pdf')
        self.assertTrue(pdf.startswith(b'%PDF'))

    def test_en_caja_lo_recibe_el_cliente_y_no_el_cajero(self):
        tx = self.pagar(self.crear_pendiente(usuario=self.cajero, canal=Transaccion.Canal.CAJA))
        self.assertEqual(tx.factura.envio_email.destinatarios, [self.EMAIL_CLIENTE])

    def test_cancelar_no_genera_factura(self):
        self.pagar(nuevo_estado=Transaccion.Estado.CANCELADA)
        self.assertFalse(FacturaElectronica.objects.exists())

    def test_transaccion_creada_ya_pagada_no_genera_factura(self):
        """Los datos de prueba se crean directamente como PAGADA y no deben facturarse."""
        with self.captureOnCommitCallbacks(execute=True):
            self.crear_pendiente(estado=Transaccion.Estado.PAGADA)
        self.assertFalse(FacturaElectronica.objects.exists())

    def test_sin_configuracion_activa_no_genera_factura(self):
        self.configuracion.activa = False
        self.configuracion.save(update_fields=['activa'])
        with self.assertLogs('comprobantes.simulacion', level='WARNING'):
            tx = self.pagar()
        self.assertFalse(FacturaElectronica.objects.filter(transaccion=tx).exists())
        self.assertFalse(tx.facturada)

    def test_no_duplica_si_la_transaccion_ya_tiene_factura(self):
        tx = self.pagar()
        self.assertIsNone(emitir_factura_simulada(tx.id))
        self.assertEqual(FacturaElectronica.objects.filter(transaccion=tx).count(), 1)


class InterruptoresTests(ComprobantesDatosMixin, TestCase):
    """El modo simulación solo actúa encendido y con la emisión real apagada."""

    def pagar(self):
        tx = self.crear_pendiente()
        with self.captureOnCommitCallbacks(execute=True):
            cambiar_estado_transaccion(tx, Transaccion.Estado.PAGADA, self.cajero)
        return tx

    @override_settings(COMPROBANTES_SIMULAR_FACTURA=False, FACTURACION_EMISION_AUTOMATICA=False)
    def test_apagado_no_genera_factura(self):
        self.pagar()
        self.assertFalse(FacturaElectronica.objects.exists())

    @override_settings(COMPROBANTES_SIMULAR_FACTURA=True, FACTURACION_EMISION_AUTOMATICA=True)
    @patch('facturacion.services.emision.emitir_factura')
    def test_con_emision_real_activa_no_simula(self, mock_emitir):
        """Con la emisión real de SCRUM-56 encendida, solo actúa la emisión real."""
        self.pagar()
        mock_emitir.assert_called_once()
        self.assertFalse(FacturaElectronica.objects.exists())


@override_settings(COMPROBANTES_SIMULAR_FACTURA=True, FACTURACION_EMISION_AUTOMATICA=False)
class KudeSimuladoTests(ComprobantesDatosMixin, TestCase):
    """El KuDE simulado muestra los datos de la factura y la leyenda de simulación."""

    def setUp(self):
        super().setUp()
        tx = self.crear_pendiente(estado=Transaccion.Estado.PAGADA)
        self.factura = emitir_factura_simulada(tx.id)

    def test_la_plantilla_incluye_los_datos_fiscales(self):
        html = render_to_string(PLANTILLA, contexto_kude(self.factura))
        for dato in ('GLOBAL EXCHANGE', '2595733-3', '02595733', '001-003-9000001', 'Ana Pérez',
                     '1111111', 'Venta de divisas USD', 'GE-VD-USD', '765.000', 'SIMULACIÓN',
                     self.factura.cdc[:4] + ' ' + self.factura.cdc[4:8]):
            self.assertIn(dato, html)

    def test_el_xml_simulado_tiene_los_datos_y_la_marca_de_simulacion(self):
        rde = ET.fromstring(generar_xml_simulado(self.factura))
        self.assertIn('SIMULACIÓN', rde.findtext('simulacion'))
        de = rde.find('DE')
        self.assertEqual(de.get('Id'), self.factura.cdc)
        self.assertEqual(de.findtext('gTimb/dNumDoc'), '9000001')
        self.assertEqual(de.findtext('gTimb/dNumTim'), '02595733')
        self.assertEqual(de.findtext('gDatGralOpe/gDatRec/dEmailRec'), self.EMAIL_CLIENTE)
        self.assertEqual(de.findtext('gDatGralOpe/gEmis/dRucEm'), '2595733')

    def test_genera_un_pdf(self):
        contenido = generar_kude_simulado(self.factura)
        self.assertTrue(contenido.startswith(b'%PDF'))
        self.assertGreater(len(contenido), 1000)
