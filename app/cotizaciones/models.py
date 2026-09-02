from django.db import models

class Cotizacion(models.Model):
    """
    Modelo que representa la cotización de compra y venta de una moneda.
    """
    # Si tus compañeros hacen el CRUD de Monedas, aquí iría un ForeignKey. 
    # Por ahora lo dejamos como CharField por simplicidad.
    moneda = models.CharField(max_length=10, help_text="Ej: USD, EUR, BRL") 
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.moneda} - C: {self.precio_compra} | V: {self.precio_venta}"