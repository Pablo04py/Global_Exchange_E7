"""Registro en el admin de Django de los envíos de facturas por email (solo lectura)."""

from django.contrib import admin

from .models import EnvioComprobante
from .simulacion import es_factura_simulada


@admin.register(EnvioComprobante)
class EnvioComprobanteAdmin(admin.ModelAdmin):
    """Permite consultar la cola de envíos y su estado sin modificarla."""

    list_display = ('numero_factura', 'cliente', 'simulada', 'estado', 'intentos', 'fecha_creacion',
                    'proximo_intento', 'fecha_envio')
    list_filter = ('estado',)
    list_select_related = ('factura', 'factura__transaccion__cliente')
    search_fields = ('factura__numero_documento', 'factura__cdc', 'destinatarios')
    readonly_fields = [f.name for f in EnvioComprobante._meta.fields] + ['cdc']

    @admin.display(description='Factura', ordering='factura__numero_documento')
    def numero_factura(self, obj):
        """Número de documento de la factura enviada."""
        return obj.factura.numero_documento

    @admin.display(description='Cliente')
    def cliente(self, obj):
        """Cliente de la transacción facturada."""
        return obj.factura.transaccion.cliente

    @admin.display(description='Simulada', boolean=True)
    def simulada(self, obj):
        """Si la factura la generó el modo simulación (sin validez fiscal)."""
        return es_factura_simulada(obj.factura)

    @admin.display(description='CDC')
    def cdc(self, obj):
        """Código de control de la factura en SIFEN."""
        return obj.factura.cdc

    def has_add_permission(self, request):
        """Los envíos solo se crean cuando una factura queda aprobada."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Se conservan como registro de auditoría."""
        return False
