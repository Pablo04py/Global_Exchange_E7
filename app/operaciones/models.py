"""Modelos de la aplicación operaciones (monedas y tasas de cambio)."""

from django.db import models


import uuid
from django.db import models


class Moneda(models.Model):
    """Moneda extranjera operada por la casa de cambios.

    Attributes:
        id: Identificador UUID, no editable.
        codigo: Código ISO 4217 de 3 letras (ej. `USD`), único.
        nombre: Nombre de la moneda.
        habilitada: Si la moneda se muestra y puede operarse.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=3, unique=True)  # ISO 4217
    nombre = models.CharField(max_length=50)
    habilitada = models.BooleanField(default=True)

    def __str__(self):
        """Devuelve el código ISO de la moneda."""
        return self.codigo

    class Meta:
        """Nombres legibles y orden alfabético por código."""
        verbose_name = "Moneda"
        verbose_name_plural = "Monedas"
        ordering = ['codigo']


class TasaDeCambio(models.Model):
    """Tasa de cambio de una moneda respecto al guaraní (PYG).

    Cada registro es histórico: la tasa vigente es la más reciente
    (ordenadas por `fecha_vigencia` descendente).

    Attributes:
        moneda: Moneda a la que pertenece la tasa.
        tasa_base: Valor de referencia en PYG.
        margen_compra: Monto que se resta a la base para el precio de compra.
        margen_venta: Monto que se suma a la base para el precio de venta.
        fecha_vigencia: Fecha y hora de registro de la tasa.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    moneda = models.ForeignKey(Moneda, on_delete=models.CASCADE, related_name='tasas')
    tasa_base = models.DecimalField(max_digits=12, decimal_places=4)
    margen_compra = models.DecimalField(max_digits=12, decimal_places=4)
    margen_venta = models.DecimalField(max_digits=12, decimal_places=4)
    fecha_vigencia = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Nombres legibles y orden de más reciente a más antigua."""
        verbose_name = "Tasa de Cambio"
        verbose_name_plural = "Tasas de Cambio"
        ordering = ['-fecha_vigencia']

    def __str__(self):
        """Devuelve `MONEDA @ dd/mm/aaaa hh:mm`."""
        return f"{self.moneda.codigo} @ {self.fecha_vigencia:%d/%m/%Y %H:%M}"

    def calcular_precio_compra(self):
        """Calcula el precio al que la casa compra la moneda.

        Returns:
            Decimal: `tasa_base - margen_compra`.
        """
        return self.tasa_base - self.margen_compra

    def calcular_precio_venta(self):
        """Calcula el precio al que la casa vende la moneda.

        Returns:
            Decimal: `tasa_base + margen_venta`.
        """
        return self.tasa_base + self.margen_venta