"""Registro en el admin de Django de los envíos de comprobantes (solo lectura)."""

from django.contrib import admin

from .models import EnvioComprobante


@admin.register(EnvioComprobante)
class EnvioComprobanteAdmin(admin.ModelAdmin):
    """Permite consultar la cola de envíos y su estado sin modificarla."""

    list_display = ('transaccion', 'estado', 'intentos', 'fecha_creacion', 'proximo_intento', 'fecha_envio')
    list_filter = ('estado',)
    search_fields = ('transaccion__id', 'destinatarios')
    readonly_fields = [f.name for f in EnvioComprobante._meta.fields]

    def has_add_permission(self, request):
        """Los envíos solo se crean al confirmarse un pago."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Se conservan como registro de auditoría."""
        return False
