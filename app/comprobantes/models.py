"""Modelos de la aplicación comprobantes (cola de envíos por email)."""

import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone

from operaciones.models import Transaccion


class EnvioComprobante(models.Model):
    """Envío por email del comprobante de una transacción pagada.

    Funciona como cola: si el servidor SMTP falla, el registro queda `PENDIENTE`
    con la fecha del próximo intento y el comando `procesar_envios` lo reintenta.
    Pasada la ventana de reintentos (1 hora por defecto) queda `FALLIDO`.

    Attributes:
        id: Identificador UUID, no editable.
        transaccion: Transacción cuyo comprobante se envía (uno por transacción).
        destinatarios: Emails de los usuarios asociados al cliente.
        estado: `PENDIENTE`, `ENVIADO` o `FALLIDO`.
        intentos: Cantidad de intentos de envío realizados.
        ultimo_error: Mensaje del último error de SMTP.
        fecha_creacion: Momento en que se encoló el envío; inicio de la ventana de reintentos.
        proximo_intento: Momento a partir del cual se puede volver a intentar.
        fecha_envio: Momento en que el correo se envió con éxito.
    """

    class Estado(models.TextChoices):
        """Estados del envío."""
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        ENVIADO = 'ENVIADO', 'Enviado'
        FALLIDO = 'FALLIDO', 'Fallido'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaccion = models.ForeignKey(Transaccion, on_delete=models.PROTECT, related_name='envios_comprobante')
    destinatarios = ArrayField(models.EmailField())
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    intentos = models.PositiveIntegerField(default=0)
    ultimo_error = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    proximo_intento = models.DateTimeField(default=timezone.now)
    fecha_envio = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Nombres legibles, orden por antigüedad y un solo envío por transacción."""
        verbose_name = "Envío de comprobante"
        verbose_name_plural = "Envíos de comprobantes"
        ordering = ['-fecha_creacion']
        constraints = [
            models.UniqueConstraint(fields=['transaccion'], name='envio_unico_por_transaccion'),
        ]
        indexes = [models.Index(fields=['estado', 'proximo_intento'])]

    def __str__(self):
        """Devuelve `Comprobante <id de transacción> - ESTADO`."""
        return f"Comprobante {self.transaccion_id} - {self.get_estado_display()}"
