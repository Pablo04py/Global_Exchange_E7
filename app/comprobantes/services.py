"""Servicios de envío por email del KuDE de las facturas y reintentos ante fallas."""

import logging
import smtplib
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from clientes.models import UsuarioCliente
from facturacion.services.factura_segura import FacturaSeguraError, FacturaSeguraService

from .models import EnvioComprobante

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
    """Emails de los usuarios activos asociados al cliente de la transacción.

    Se usa la relación `UsuarioCliente` y no `transaccion.usuario`, porque en
    las operaciones de caja ese usuario es el cajero y no el cliente.

    Args:
        transaccion: Transacción facturada.

    Returns:
        list[str]: Emails únicos, en minúsculas y ordenados; vacía si ningún
        usuario del cliente tiene email cargado.
    """
    emails = UsuarioCliente.objects.filter(
        cliente=transaccion.cliente, usuario__is_active=True
    ).values_list('usuario__email', flat=True)
    return sorted({email.strip().lower() for email in emails if email and email.strip()})


def nombre_archivo(factura):
    """Nombre del adjunto, igual al de la descarga del KuDE de `facturacion`.

    Args:
        factura: Factura electrónica.

    Returns:
        str: `factura_<número de documento>.pdf`.
    """
    return f"factura_{factura.numero_documento}.pdf"


def encolar_envio(factura):
    """Registra el envío del KuDE de una factura aprobada.

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
            "Factura %s no enviada: el cliente %s no tiene usuarios con email.",
            factura.numero_documento, factura.transaccion.cliente_id,
        )
        return None

    ahora = timezone.now()
    envio, _ = EnvioComprobante.objects.get_or_create(
        factura=factura,
        defaults={'destinatarios': destinatarios, 'fecha_creacion': ahora, 'proximo_intento': ahora},
    )
    return envio


def _enviar_email(envio):
    """Descarga el KuDE de Factura Segura y lo envía por SMTP como adjunto.

    Args:
        envio: Envío a realizar.

    Raises:
        FacturaSeguraError: Si no se pudo descargar el KuDE.
        smtplib.SMTPException | OSError: Si el servidor SMTP no responde o rechaza el envío.
    """
    factura = envio.factura
    kude = FacturaSeguraService.descargar_kude(ruc_emisor=factura.configuracion.ruc_emisor, cdc=factura.cdc)
    tx = factura.transaccion
    mensaje = EmailMessage(
        subject=f"Global Exchange - Factura electrónica N.° {factura.numero_documento}",
        body=render_to_string('comprobantes/email_factura.txt', {'factura': factura, 'transaccion': tx}),
        to=envio.destinatarios,
    )
    mensaje.attach(nombre_archivo(factura), kude, 'application/pdf')
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
        _enviar_email(envio)
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
