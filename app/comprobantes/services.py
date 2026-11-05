"""Servicios de envío por email de la factura (KuDE y XML) y reintentos ante fallas."""

import logging
import smtplib
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from facturacion.services.factura_segura import FacturaSeguraError, FacturaSeguraService

from .destinatarios import email_receptor_factura
from .kude import generar_kude_simulado, generar_xml_simulado
from .models import EnvioComprobante
from .simulacion import es_factura_simulada

logger = logging.getLogger(__name__)

# Errores transitorios: el servidor SMTP o Factura Segura no están disponibles. Se reintenta.
ERRORES_REINTENTABLES = (smtplib.SMTPException, OSError, FacturaSeguraError)


def minutos_entre_reintentos():
    """Minutos de espera entre un intento fallido y el siguiente.

    Returns:
        int: `EMAIL_REINTENTO_MINUTOS` (5 por defecto).
    """
    return getattr(settings, 'EMAIL_REINTENTO_MINUTOS', 5)


def ventana_de_reintentos():
    """Tiempo durante el cual se reintenta un envío desde que se encoló.

    Returns:
        timedelta: `EMAIL_REINTENTO_VENTANA_MINUTOS` (60 por defecto).
    """
    return timedelta(minutes=getattr(settings, 'EMAIL_REINTENTO_VENTANA_MINUTOS', 60))


def obtener_destinatarios(transaccion):
    """Destinatario del correo: el cliente que hizo la operación.

    Es el mismo email que va en el Documento Electrónico (`dEmailRec`), así el
    envío propio y el de Factura Segura llegan a la misma persona. En caja no
    es el cajero, sino la cuenta del cliente (ver `comprobantes.destinatarios`).

    Args:
        transaccion: Transacción facturada.

    Returns:
        list[str]: Un email, o lista vacía si el cliente no tiene ninguno.
    """
    email = email_receptor_factura(transaccion)
    return [email] if email else []


def es_ambiente_prueba():
    """Indica si Factura Segura apunta a su ambiente de pruebas (TEST).

    Returns:
        bool: `True` si `FACTURA_SEGURA_BASE_URL` es la API de test (`apitest`).
    """
    return 'apitest' in getattr(settings, 'FACTURA_SEGURA_BASE_URL', '')


def numero_completo(factura):
    """Número de factura con establecimiento y punto de expedición.

    Args:
        factura: Factura electrónica.

    Returns:
        str: Por ejemplo `001-003-0000217`.
    """
    config = factura.configuracion
    return f"{config.establecimiento}-{config.punto_expedicion}-{factura.numero_documento}"


def leyenda_ambiente(factura):
    """Leyenda del ambiente, como la que usa Factura Segura en sus correos.

    Args:
        factura: Factura electrónica.

    Returns:
        str: Texto del ambiente; vacío en producción.
    """
    if es_factura_simulada(factura):
        return 'DE simulado localmente - sin valor comercial ni fiscal'
    if es_ambiente_prueba():
        return 'DE generado en ambiente de prueba - sin valor comercial ni fiscal'
    return ''


def asunto_email(factura):
    """Asunto del correo, con el mismo formato que el de Factura Segura.

    Args:
        factura: Factura electrónica.

    Returns:
        str: Por ejemplo `TEST KuDE Factura electrónica 001-003-0000217 - DE generado
        en ambiente de prueba - sin valor comercial ni fiscal`.
    """
    asunto = f"KuDE Factura electrónica {numero_completo(factura)}"
    if es_factura_simulada(factura):
        return f"SIMULACIÓN {asunto} - {leyenda_ambiente(factura)}"
    if es_ambiente_prueba():
        return f"TEST {asunto} - {leyenda_ambiente(factura)}"
    return asunto


def nombres_adjuntos(factura, momento=None):
    """Nombres del XML y del KuDE, con el formato de Factura Segura.

    Args:
        factura: Factura electrónica.
        momento: Fecha y hora del envío (por defecto, ahora).

    Returns:
        tuple[str, str]: `<CDC>.xml` y `<CDC>_<AAAAMMDD>_<HHMMSS>.pdf`.
    """
    momento = timezone.localtime(momento or timezone.now())
    return f"{factura.cdc}.xml", f"{factura.cdc}_{momento:%Y%m%d_%H%M%S}.pdf"


def obtener_adjuntos(factura, momento=None):
    """XML y KuDE de la factura, en el orden en que los adjunta Factura Segura.

    Args:
        factura: Factura aprobada.
        momento: Fecha y hora del envío, para el nombre del PDF.

    Returns:
        list[tuple[str, bytes, str]]: `(nombre, contenido, tipo MIME)` del XML y del PDF.
        Si la factura es simulada (ver `comprobantes.simulacion`) se generan
        localmente; si no, se descargan de Factura Segura.

    Raises:
        FacturaSeguraError: Si no se pudo descargar el XML o el KuDE real.
    """
    nombre_xml, nombre_pdf = nombres_adjuntos(factura, momento)
    if es_factura_simulada(factura):
        xml, kude = generar_xml_simulado(factura), generar_kude_simulado(factura)
    else:
        ruc, cdc = factura.configuracion.ruc_emisor, factura.cdc
        xml = FacturaSeguraService.descargar_xml(ruc_emisor=ruc, cdc=cdc)
        kude = FacturaSeguraService.descargar_kude(ruc_emisor=ruc, cdc=cdc)
    return [(nombre_xml, xml, 'application/xml'), (nombre_pdf, kude, 'application/pdf')]


def encolar_envio(factura):
    """Registra el envío de la factura aprobada.

    Solo crea el registro `PENDIENTE`; el correo lo manda el comando
    `procesar_envios` (servicio `mailer`). Así quien aprobó la factura, por
    ejemplo la vista de detalle de la transacción, no espera la descarga del
    KuDE ni la respuesta del SMTP. Si la factura ya tiene un envío no se crea
    otro, para que nunca se manden dos correos.

    Args:
        factura: Factura que acaba de quedar `APROBADA`.

    Returns:
        EnvioComprobante | None: El envío, o `None` si el cliente no tiene
        ningún email al que enviarlo.
    """
    destinatarios = obtener_destinatarios(factura.transaccion)
    if not destinatarios:
        logger.warning(
            "Factura %s no enviada: el cliente %s no tiene un correo electrónico registrado.",
            factura.numero_documento, factura.transaccion.cliente_id,
        )
        return None

    ahora = timezone.now()
    envio, _ = EnvioComprobante.objects.get_or_create(
        factura=factura,
        defaults={'destinatarios': destinatarios, 'fecha_creacion': ahora, 'proximo_intento': ahora},
    )
    return envio


def _enviar_email(envio, ahora=None):
    """Arma el correo con el XML y el KuDE adjuntos y lo envía por SMTP.

    Args:
        envio: Envío a realizar.
        ahora: Momento del envío, para el nombre del PDF.

    Raises:
        FacturaSeguraError: Si no se pudo descargar el XML o el KuDE.
        smtplib.SMTPException | OSError: Si el servidor SMTP no responde o rechaza el envío.
    """
    factura = envio.factura
    adjuntos = obtener_adjuntos(factura, ahora)
    mensaje = EmailMessage(
        subject=asunto_email(factura),
        body=render_to_string('comprobantes/email_factura.txt', {
            'factura': factura,
            'transaccion': factura.transaccion,
            'numero_completo': numero_completo(factura),
            'leyenda_ambiente': leyenda_ambiente(factura),
            'simulada': es_factura_simulada(factura),
        }),
        to=envio.destinatarios,
    )
    for nombre, contenido, tipo in adjuntos:
        mensaje.attach(nombre, contenido, tipo)
    mensaje.send(fail_silently=False)


def intentar_envio(envio, ahora=None):
    """Intenta enviar el KuDE y actualiza el estado del envío.

    - Si el correo sale: queda `ENVIADO`.
    - Si el SMTP o Factura Segura fallan dentro de la ventana de reintentos:
      sigue `PENDIENTE` y se programa el próximo intento (nunca después del fin
      de la ventana).
    - Si fallan con la ventana vencida, o el error es de otro tipo: queda `FALLIDO`.

    Args:
        envio: Envío `PENDIENTE` a intentar.
        ahora: Momento del intento (por defecto, `timezone.now()`).

    Returns:
        EnvioComprobante: El envío actualizado.
    """
    ahora = ahora or timezone.now()
    envio.intentos += 1
    try:
        _enviar_email(envio, ahora)
    except ERRORES_REINTENTABLES as exc:
        envio.ultimo_error = f"{type(exc).__name__}: {exc}"
        limite = envio.fecha_creacion + ventana_de_reintentos()
        if ahora >= limite:
            envio.estado = EnvioComprobante.Estado.FALLIDO
            logger.error("Envío %s FALLIDO tras %s intentos: %s", envio.id, envio.intentos, envio.ultimo_error)
        else:
            envio.proximo_intento = min(ahora + timedelta(minutes=minutos_entre_reintentos()), limite)
            logger.warning("Envío %s se reintentará a las %s: %s",
                           envio.id, envio.proximo_intento, envio.ultimo_error)
    except Exception as exc:
        envio.estado = EnvioComprobante.Estado.FALLIDO
        envio.ultimo_error = f"{type(exc).__name__}: {exc}"
        logger.exception("Envío %s FALLIDO por un error no reintentable.", envio.id)
    else:
        envio.estado = EnvioComprobante.Estado.ENVIADO
        envio.fecha_envio = ahora
        envio.ultimo_error = ''
    envio.save(update_fields=['estado', 'intentos', 'ultimo_error', 'proximo_intento', 'fecha_envio'])
    return envio


def procesar_pendientes(ahora=None):
    """Envía los envíos `PENDIENTE` cuyo próximo intento ya llegó.

    Cada envío se bloquea con `select_for_update(skip_locked=True)`, así dos
    procesos ejecutando el comando a la vez no mandan el mismo correo.

    Args:
        ahora: Momento de referencia (por defecto, `timezone.now()`).

    Returns:
        dict: Cantidad de envíos `procesados`, `enviados` y `fallidos` en esta pasada.
    """
    ahora = ahora or timezone.now()
    resumen = {'procesados': 0, 'enviados': 0, 'fallidos': 0}
    ids = list(EnvioComprobante.objects.filter(
        estado=EnvioComprobante.Estado.PENDIENTE, proximo_intento__lte=ahora,
    ).order_by('proximo_intento').values_list('id', flat=True))

    for envio_id in ids:
        with transaction.atomic():
            envio = EnvioComprobante.objects.select_for_update(skip_locked=True).filter(
                id=envio_id, estado=EnvioComprobante.Estado.PENDIENTE,
            ).first()
            if envio is None:
                continue  # lo tomó otro proceso o ya cambió de estado
            intentar_envio(envio, ahora)
        resumen['procesados'] += 1
        if envio.estado == EnvioComprobante.Estado.ENVIADO:
            resumen['enviados'] += 1
        elif envio.estado == EnvioComprobante.Estado.FALLIDO:
            resumen['fallidos'] += 1
    return resumen
