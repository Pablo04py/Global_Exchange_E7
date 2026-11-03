"""Servicios de envío por email de comprobantes y reintentos ante fallas del SMTP."""

import logging
import smtplib
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from clientes.models import UsuarioCliente

from .models import EnvioComprobante
from .pdf import generar_pdf_comprobante, nombre_archivo

logger = logging.getLogger(__name__)

# Errores que indican que el servidor SMTP no está disponible: se reintenta.
ERRORES_SMTP = (smtplib.SMTPException, OSError)


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
        transaccion: Transacción pagada.

    Returns:
        list[str]: Emails únicos, en minúsculas y ordenados; vacía si ningún
        usuario del cliente tiene email cargado.
    """
    emails = UsuarioCliente.objects.filter(
        cliente=transaccion.cliente, usuario__is_active=True
    ).values_list('usuario__email', flat=True)
    return sorted({email.strip().lower() for email in emails if email and email.strip()})


def encolar_envio(transaccion):
    """Registra el envío del comprobante y hace el primer intento.

    Si la transacción ya tiene un envío registrado no se crea otro, así un
    mismo pago nunca genera dos correos.

    Args:
        transaccion: Transacción que acaba de pasar a `PAGADA`.

    Returns:
        EnvioComprobante | None: El envío, o `None` si el cliente no tiene
        ningún email al que enviarlo.
    """
    destinatarios = obtener_destinatarios(transaccion)
    if not destinatarios:
        logger.warning(
            "Comprobante de la transacción %s no enviado: el cliente %s no tiene usuarios con email.",
            transaccion.id, transaccion.cliente_id,
        )
        return None

    ahora = timezone.now()
    envio, creado = EnvioComprobante.objects.get_or_create(
        transaccion=transaccion,
        defaults={
            'destinatarios': destinatarios,
            'fecha_creacion': ahora,
            # Mientras se hace el primer intento, el comando de reintentos no lo toma.
            'proximo_intento': ahora + timedelta(minutes=minutos_entre_reintentos()),
        },
    )
    if creado:
        intentar_envio(envio, ahora)
    return envio


def _enviar_email(envio):
    """Arma el correo con el PDF adjunto y lo envía por SMTP.

    Args:
        envio: Envío a realizar.

    Raises:
        smtplib.SMTPException | OSError: Si el servidor SMTP no responde o rechaza el envío.
    """
    tx = envio.transaccion
    mensaje = EmailMessage(
        subject=f"Global Exchange - Comprobante de su operación del {timezone.localtime(tx.fecha):%d/%m/%Y}",
        body=render_to_string('comprobantes/email_comprobante.txt', {'transaccion': tx}),
        to=envio.destinatarios,
    )
    mensaje.attach(nombre_archivo(tx), generar_pdf_comprobante(tx), 'application/pdf')
    mensaje.send(fail_silently=False)


def intentar_envio(envio, ahora=None):
    """Intenta enviar el comprobante y actualiza el estado del envío.

    - Si el correo sale: queda `ENVIADO`.
    - Si el SMTP falla dentro de la ventana de reintentos: sigue `PENDIENTE`
      y se programa el próximo intento (nunca después del fin de la ventana).
    - Si el SMTP falla con la ventana vencida, o el error no es de SMTP (por
      ejemplo, no se pudo generar el PDF): queda `FALLIDO`.

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
    except ERRORES_SMTP as exc:
        envio.ultimo_error = f"{type(exc).__name__}: {exc}"
        limite = envio.fecha_creacion + ventana_de_reintentos()
        if ahora >= limite:
            envio.estado = EnvioComprobante.Estado.FALLIDO
            logger.error("Envío %s FALLIDO tras %s intentos: %s", envio.id, envio.intentos, envio.ultimo_error)
        else:
            envio.proximo_intento = min(ahora + timedelta(minutes=minutos_entre_reintentos()), limite)
            logger.warning("Envío %s encolado para reintento a las %s: %s",
                           envio.id, envio.proximo_intento, envio.ultimo_error)
    except Exception as exc:
        envio.estado = EnvioComprobante.Estado.FALLIDO
        envio.ultimo_error = f"{type(exc).__name__}: {exc}"
        logger.exception("Envío %s FALLIDO por un error que no es de SMTP.", envio.id)
    else:
        envio.estado = EnvioComprobante.Estado.ENVIADO
        envio.fecha_envio = ahora
        envio.ultimo_error = ''
    envio.save(update_fields=['estado', 'intentos', 'ultimo_error', 'proximo_intento', 'fecha_envio'])
    return envio


def procesar_pendientes(ahora=None):
    """Reintenta los envíos `PENDIENTE` cuyo próximo intento ya llegó.

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
