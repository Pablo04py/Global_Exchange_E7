"""KuDE y XML simulados de una factura simulada (SCRUM-23).

Las facturas simuladas no existen en Factura Segura, así que su PDF se genera
localmente con el mismo contenido que un KuDE real (emisor, timbrado, receptor,
ítem, total y CDC) y la leyenda de que no tiene validez fiscal. Los montos y
descripciones se obtienen con las mismas funciones que usa SCRUM-56 para armar
el Documento Electrónico. El XML simulado imita la estructura `rDE` del XML real
para que el correo lleve los mismos dos adjuntos que envía Factura Segura.
"""

from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from xml.etree import ElementTree as ET

from django.template.loader import render_to_string
from django.utils import timezone
from xhtml2pdf import pisa

from clientes.models import Cliente
from comprobantes.destinatarios import email_receptor_factura
from facturacion.services.factura_builder import (
    obtener_codigo_item,
    obtener_descripcion_operacion,
    obtener_monto_factura,
)

PLANTILLA = 'comprobantes/kude_simulado.html'


def formatear_guaranies(monto):
    """Formatea un monto en guaraníes sin decimales y con punto de miles.

    Args:
        monto: Monto en PYG.

    Returns:
        str: Por ejemplo `2.444` o `1.250.000`.
    """
    entero = Decimal(monto).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return f"{int(entero):,}".replace(',', '.')


def contexto_kude(factura):
    """Datos que muestra el KuDE simulado.

    Args:
        factura: Factura simulada.

    Returns:
        dict: Contexto para la plantilla `comprobantes/kude_simulado.html`.
    """
    tx = factura.transaccion
    config = factura.configuracion
    cliente = tx.cliente
    actividades = config.actividades_economicas or []
    if cliente.tipo_persona == Cliente.TipoPersona.JURIDICA and cliente.digito_verificador:
        documento_receptor = ('RUC', f"{cliente.documento}-{cliente.digito_verificador}")
    else:
        documento_receptor = ('Documento de identidad', cliente.documento)
    return {
        'factura': factura,
        'transaccion': tx,
        'config': config,
        'actividad': actividades[0].get('dDesActEco', '') if actividades else '',
        'numero_completo': f"{config.establecimiento}-{config.punto_expedicion}-{factura.numero_documento}",
        'fecha_emision': timezone.localtime(factura.fecha_creacion or timezone.now()),
        'documento_receptor': documento_receptor,
        'email_receptor': email_receptor_factura(tx),
        'descripcion': obtener_descripcion_operacion(tx),
        'codigo_item': obtener_codigo_item(tx),
        'total': formatear_guaranies(obtener_monto_factura(tx)),
        'cdc_agrupado': ' '.join(factura.cdc[i:i + 4] for i in range(0, len(factura.cdc), 4)),
    }


def generar_kude_simulado(factura):
    """Genera el PDF del KuDE simulado de la factura.

    Args:
        factura: Factura simulada.

    Returns:
        bytes: Contenido del archivo PDF.

    Raises:
        RuntimeError: Si xhtml2pdf no pudo convertir la plantilla.
    """
    html = render_to_string(PLANTILLA, contexto_kude(factura))
    salida = BytesIO()
    resultado = pisa.CreatePDF(html, dest=salida, encoding='utf-8')
    if resultado.err:
        raise RuntimeError(f"No se pudo generar el KuDE simulado de la factura {factura.numero_documento}.")
    return salida.getvalue()


def generar_xml_simulado(factura):
    """Genera el XML simulado de la factura, con estructura parecida al `rDE` de SIFEN.

    Args:
        factura: Factura simulada.

    Returns:
        bytes: Documento XML en UTF-8, con la marca de que no tiene validez fiscal.
    """
    datos = contexto_kude(factura)
    tx, config = factura.transaccion, factura.configuracion
    rde = ET.Element('rDE')
    ET.SubElement(rde, 'simulacion').text = (
        'SIMULACIÓN SCRUM-23: no emitido en SIFEN, sin valor comercial ni fiscal')
    de = ET.SubElement(rde, 'DE', Id=factura.cdc)
    timbrado = ET.SubElement(de, 'gTimb')
    for campo, valor in (('iTiDE', '1'), ('dDesTiDE', 'Factura electrónica'), ('dNumTim', config.timbrado),
                         ('dEst', config.establecimiento), ('dPunExp', config.punto_expedicion),
                         ('dNumDoc', factura.numero_documento),
                         ('dFeIniT', config.fecha_inicio_timbrado.isoformat())):
        ET.SubElement(timbrado, campo).text = valor
    generales = ET.SubElement(de, 'gDatGralOpe')
    ET.SubElement(generales, 'dFeEmiDE').text = datos['fecha_emision'].strftime('%Y-%m-%dT%H:%M:%S')
    emisor = ET.SubElement(generales, 'gEmis')
    for campo, valor in (('dRucEm', config.ruc_emisor), ('dDVEmi', config.dv_emisor),
                         ('dNomEmi', config.nombre_emisor), ('dDirEmi', config.direccion),
                         ('dEmailE', config.email)):
        ET.SubElement(emisor, campo).text = valor or ''
    receptor = ET.SubElement(generales, 'gDatRec')
    for campo, valor in (('dNomRec', tx.cliente.nombre_o_denominacion), ('dNumIDRec', datos['documento_receptor'][1]),
                         ('dEmailRec', datos['email_receptor'])):
        ET.SubElement(receptor, campo).text = valor or ''
    item = ET.SubElement(ET.SubElement(de, 'gDtipDE'), 'gCamItem')
    for campo, valor in (('dCodInt', datos['codigo_item']), ('dDesProSer', datos['descripcion']),
                         ('dCantProSer', '1'), ('dTotOpeItem', str(obtener_monto_factura(tx)))):
        ET.SubElement(item, campo).text = valor
    ET.SubElement(ET.SubElement(de, 'gTotSub'), 'dTotGralOpe').text = str(obtener_monto_factura(tx))
    return ET.tostring(rde, encoding='utf-8', xml_declaration=True)
