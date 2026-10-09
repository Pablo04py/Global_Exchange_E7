"""Modelos de la aplicación arqueos (cierre de caja y arqueo, SCRUM-40)."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ArqueoCaja(models.Model):
    """Registro formal del cierre de una caja.

    Guarda una "foto" de la caja al momento del cierre (identificador, nombre
    y sucursal) en lugar de una clave foránea al modelo de caja, que pertenece
    a otra historia. Así el arqueo no depende de ese modelo y conserva los
    datos aunque la caja se renombre o se elimine.

    Es un registro de auditoría: una vez guardado no se puede modificar
    (ver `save`). El detalle por moneda está en `DetalleArqueo`.

    Attributes:
        id: Identificador UUID, no editable.
        caja_id: Identificador de la caja cerrada (clave primaria en su modelo).
        caja_nombre: Nombre de la caja al momento del cierre.
        sucursal_nombre: Sucursal de la caja al momento del cierre.
        cajero: Usuario que realizó el cierre.
        fecha_cierre: Fecha y hora del cierre.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    caja_id = models.CharField(max_length=64)
    caja_nombre = models.CharField(max_length=150)
    sucursal_nombre = models.CharField(max_length=150, blank=True)
    cajero = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='arqueos')
    fecha_cierre = models.DateTimeField(default=timezone.now)

    class Meta:
        """Nombres legibles y orden del más reciente al más antiguo."""
        verbose_name = "Arqueo de caja"
        verbose_name_plural = "Arqueos de caja"
        ordering = ['-fecha_cierre']

    def __str__(self):
        """Devuelve `Arqueo <caja> - dd/mm/aaaa hh:mm`."""
        return f"Arqueo {self.caja_nombre} - {self.fecha_cierre:%d/%m/%Y %H:%M}"

    def save(self, *args, **kwargs):
        """Guarda el arqueo solo la primera vez.

        Raises:
            ValidationError: Si se intenta modificar un arqueo ya registrado.
        """
        if not self._state.adding:
            raise ValidationError("Un arqueo registrado no se puede modificar.")
        super().save(*args, **kwargs)

    @property
    def tiene_discrepancias(self):
        """Indica si alguna moneda tuvo sobrante o faltante.

        Returns:
            bool: `True` si al menos un detalle no cuadra.
        """
        return self.detalles.exclude(resultado=DetalleArqueo.Resultado.CUADRA).exists()


class DetalleArqueo(models.Model):
    """Resultado del arqueo para una moneda.

    Attributes:
        arqueo: Arqueo al que pertenece.
        moneda: Código ISO 4217 de la moneda (ej. `PYG`, `USD`).
        saldo_registrado: Saldo que el sistema esperaba en la caja.
        saldo_declarado: Saldo físico contado y declarado por el cajero.
        diferencia: `saldo_declarado - saldo_registrado`.
        resultado: `CUADRA`, `SOBRANTE` o `FALTANTE`.
    """

    class Resultado(models.TextChoices):
        """Resultado de comparar el saldo declarado con el registrado."""
        CUADRA = 'CUADRA', 'Cuadra'
        SOBRANTE = 'SOBRANTE', 'Sobrante'
        FALTANTE = 'FALTANTE', 'Faltante'

    arqueo = models.ForeignKey(ArqueoCaja, on_delete=models.CASCADE, related_name='detalles')
    moneda = models.CharField(max_length=3)
    saldo_registrado = models.DecimalField(max_digits=18, decimal_places=2)
    saldo_declarado = models.DecimalField(max_digits=18, decimal_places=2)
    diferencia = models.DecimalField(max_digits=18, decimal_places=2)
    resultado = models.CharField(max_length=10, choices=Resultado.choices)

    class Meta:
        """Una fila por moneda en cada arqueo, ordenadas por código."""
        verbose_name = "Detalle de arqueo"
        verbose_name_plural = "Detalles de arqueo"
        ordering = ['moneda']
        constraints = [
            models.UniqueConstraint(fields=['arqueo', 'moneda'], name='detalle_arqueo_moneda_unica'),
        ]

    def __str__(self):
        """Devuelve `MONEDA: Resultado (diferencia)`."""
        return f"{self.moneda}: {self.get_resultado_display()} ({self.diferencia})"

    def save(self, *args, **kwargs):
        """Guarda el detalle solo la primera vez.

        Raises:
            ValidationError: Si se intenta modificar un detalle ya registrado.
        """
        if not self._state.adding:
            raise ValidationError("Un detalle de arqueo registrado no se puede modificar.")
        super().save(*args, **kwargs)
