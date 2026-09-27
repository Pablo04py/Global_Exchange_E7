"""Registro de `Moneda`, `TasaDeCambio` y `Transaccion` en el panel de administración."""

from django.contrib import admin
from .models import Moneda, TasaDeCambio, Transaccion

admin.site.register(Moneda)
admin.site.register(TasaDeCambio)


@admin.register(Transaccion)
class TransaccionAdmin(admin.ModelAdmin):
    """Consulta de transacciones en el admin.

    Permite dar de alta transacciones de prueba, pero no editarlas ni
    eliminarlas, ya que son registros de auditoría.
    """
    list_display = ('fecha', 'usuario', 'tipo', 'moneda', 'monto_pagado', 'monto_recibido', 'estado', 'cajero')
    list_filter = ('tipo', 'estado', 'moneda', 'facturada', 'dispositivo')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name', 'cajero__username')
    date_hierarchy = 'fecha'

    def has_change_permission(self, request, obj=None):
        """Las transacciones registradas no se modifican."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Las transacciones registradas no se eliminan."""
        return False
