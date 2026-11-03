"""Modelos de la aplicación comprobantes (cola de envíos de facturas por email)."""

import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone

from facturacion.models import FacturaElectronica


class EnvioComprobante(models.Model):
    """Envío por email del KuDE de una factura electrónica aprobada.

    Funciona como cola: el envío se crea `PENDIENTE` cuando la factura pasa a
    `APROBADA` y lo procesa el comando `procesar_envios`. Si el servidor SMTP o
    Factura Segura fallan, se programa el próximo intento; pasada la ventana de
    reintentos (1 hora por defecto) queda `FALLIDO`.

    Attributes:
        id: Identificador UUID, no editable.
        factura: Factura cuyo KuDE se envía (un envío por factura).
        destinatarios: Emails de los usuarios asociados al cliente.
        estado: `PENDIENTE`, `ENVIADO` o `FALLIDO`.
        intentos: Cantidad de intentos de envío realizados.
        ultimo_error: Mensaje del último error.
        fecha_creacion: Momento en que se encoló el envío; inicio de la ventana de reintentos.
        proximo_intento: Momento a partir del cual se puede intentar el envío.
        fecha_envio: Momento en que el correo se envió con éxito.
    """

    class Estado(models.TextChoices):
        """Estados del envío."""
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        ENVIADO = 'ENVIADO', 'Enviado'
        FALLIDO = 'FALLIDO', 'Fallido'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    factura = models.OneToOneField(FacturaElectronica, on_delete=models.PROTECT, related_name='envio_email')
    destinatarios = ArrayField(models.EmailField())
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    intentos = models.PositiveIntegerField(default=0)
    ultimo_error = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    proximo_intento = models.DateTimeField(default=timezone.now)
    fecha_envio = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Nombres legibles, orden por antigüedad e índice para buscar pendientes."""
        verbose_name = "Envío de factura por email"
        verbose_name_plural = "Envíos de facturas por email"
        ordering = ['-fecha_creacion']
        indexes = [models.Index(fields=['estado', 'proximo_intento'])]

    def __str__(self):
        """Devuelve `Factura <número> - ESTADO`."""
        return f"Factura {self.factura.numero_documento} - {self.get_estado_display()}"
