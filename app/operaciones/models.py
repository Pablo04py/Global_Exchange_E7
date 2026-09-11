from django.db import models


import uuid
from django.db import models


class Moneda(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=3, unique=True)  # ISO 4217
    nombre = models.CharField(max_length=50)
    habilitada = models.BooleanField(default=True)

    def __str__(self):
        return self.codigo

    class Meta:
        verbose_name = "Moneda"
        verbose_name_plural = "Monedas"
        ordering = ['codigo']


class TasaDeCambio(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    moneda = models.ForeignKey(Moneda, on_delete=models.CASCADE, related_name='tasas')
    tasa_base = models.DecimalField(max_digits=12, decimal_places=4)
    margen_compra = models.DecimalField(max_digits=12, decimal_places=4)
    margen_venta = models.DecimalField(max_digits=12, decimal_places=4)
    fecha_vigencia = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tasa de Cambio"
        verbose_name_plural = "Tasas de Cambio"
        ordering = ['-fecha_vigencia']

    def __str__(self):
        return f"{self.moneda.codigo} @ {self.fecha_vigencia:%d/%m/%Y %H:%M}"

    def calcular_precio_compra(self):
        return self.tasa_base - self.margen_compra

    def calcular_precio_venta(self):
        return self.tasa_base + self.margen_venta