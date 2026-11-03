"""Generación del PDF del comprobante de una transacción.

Mientras no exista la factura electrónica (SCRUM-22/56) el PDF es un comprobante
provisorio armado con los datos de la `Transaccion`. Cuando esté el KuDE, solo
hay que reemplazar `generar_pdf_comprobante`; la cola y el envío no cambian.
"""

from io import BytesIO

from django.template.loader import render_to_string
from xhtml2pdf import pisa

PLANTILLA = 'comprobantes/comprobante_pdf.html'


def generar_pdf_comprobante(transaccion):
    """Genera el PDF del comprobante de la transacción.

    Args:
        transaccion: Transacción pagada.

    Returns:
        bytes: Contenido del archivo PDF.

    Raises:
        RuntimeError: Si xhtml2pdf no pudo convertir la plantilla.
    """
    html = render_to_string(PLANTILLA, {'transaccion': transaccion})
    salida = BytesIO()
    resultado = pisa.CreatePDF(html, dest=salida, encoding='utf-8')
    if resultado.err:
        raise RuntimeError(f"No se pudo generar el PDF del comprobante {transaccion.id}.")
    return salida.getvalue()


def nombre_archivo(transaccion):
    """Nombre del adjunto del comprobante.

    Args:
        transaccion: Transacción del comprobante.

    Returns:
        str: `comprobante-<id>.pdf`.
    """
    return f"comprobante-{transaccion.id}.pdf"
