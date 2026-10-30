from django.contrib import admin

from .models import (
    ConfiguracionFacturacion,
    FacturaElectronica,
)


@admin.register(ConfiguracionFacturacion)
class ConfiguracionFacturacionAdmin(admin.ModelAdmin):
    list_display = (
        'nombre_emisor',
        'ruc_emisor',
        'timbrado',
        'establecimiento',
        'punto_expedicion',
        'siguiente_numero_documento',
        'activa',
    )

    list_filter = (
        'activa',
    )


@admin.register(FacturaElectronica)
class FacturaElectronicaAdmin(admin.ModelAdmin):
    list_display = ('numero_documento', 'transaccion', 'estado', 'cdc', 'fecha_creacion',)

    list_filter = ('estado', 'fecha_creacion',)

    search_fields = ('numero_documento', 'cdc',)

    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')