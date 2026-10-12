""" Modelos de la aplicacion de notificaciones."""

import uuid

from django.conf import settings
from django.db import models

class Notificacion(models.Model):
    """
    Representa un aviso generado por el sistema.

    Una notificación se crea una sola vez y puede ser recibida
    por varios usuarios mediante NotificacionUsuario.
    """

    class Tipo(models.TextChoices):
        TASA_CAMBIO = 'TASA_CAMBIO', 'Cambio de tasa'
        PAGO = 'PAGO', 'Pago'
        OPERACION = 'OPERACION', 'Operación'
        SISTEMA = 'SISTEMA', 'Sistema'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices
    )

    titulo = models.CharField(
        max_length=150
    )

    mensaje = models.TextField()

    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notificaciones_creadas'
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return self.titulo


class NotificacionUsuario(models.Model):
    """
    Relaciona una notificación con cada usuario destinatario.

    Permite conocer de forma independiente si cada usuario
    ya leyó o no una notificación.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    notificacion = models.ForeignKey(
        Notificacion,
        on_delete=models.CASCADE,
        related_name='destinatarios'
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificaciones'
    )

    leida = models.BooleanField(
        default=False
    )

    fecha_lectura = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Notificación de usuario'
        verbose_name_plural = 'Notificaciones de usuarios'

        constraints = [
            models.UniqueConstraint(
                fields=['notificacion', 'usuario'],
                name='notificacion_usuario_unica'
            )
        ]

        ordering = ['-notificacion__fecha_creacion']

    def __str__(self):
        estado = 'Leída' if self.leida else 'No leída'
        return f'{self.usuario} - {self.notificacion.titulo} - {estado}'
