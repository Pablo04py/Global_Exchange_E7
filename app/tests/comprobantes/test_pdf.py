"""Pruebas de la generación del PDF del comprobante (SCRUM-23)."""

from django.template.loader import render_to_string
from django.test import TestCase

from comprobantes.pdf import PLANTILLA, generar_pdf_comprobante, nombre_archivo

from .apoyo import ComprobantesDatosMixin


class PdfComprobanteTests(ComprobantesDatosMixin, TestCase):
    """El comprobante es un PDF válido con los datos de la transacción."""

    def test_genera_un_pdf(self):
        tx = self.crear_pendiente()
        contenido = generar_pdf_comprobante(tx)
        self.assertTrue(contenido.startswith(b'%PDF'))
        self.assertGreater(len(contenido), 1000)

    def test_la_plantilla_incluye_los_datos_de_la_operacion(self):
        tx = self.crear_pendiente()
        html = render_to_string(PLANTILLA, {'transaccion': tx})
        # LANGUAGE_CODE es-py: los decimales se muestran con coma.
        for dato in (str(tx.id), 'Ana Pérez', '1111111', 'USD', '765000,00', '100,00', '7650,0000'):
            self.assertIn(dato, html)

    def test_nombre_del_adjunto(self):
        tx = self.crear_pendiente()
        self.assertEqual(nombre_archivo(tx), f'comprobante-{tx.id}.pdf')
