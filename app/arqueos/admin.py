"""Registro de los arqueos de caja en el panel de administración (solo consulta)."""

from django.contrib import admin
from .models import ArqueoCaja, DetalleArqueo


class DetalleArqueoInline(admin.TabularInline):
    """Detalle por moneda dentro del arqueo, solo lectura."""
    model = DetalleArqueo
    fields = ('moneda', 'saldo_registrado', 'saldo_declarado', 'diferencia', 'resultado')
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        """Los detalles solo se crean al cerrar la caja."""
        return False


@admin.register(ArqueoCaja)
class ArqueoCajaAdmin(admin.ModelAdmin):
    """Consulta de arqueos en el admin.

    Los arqueos son registros de auditoría: solo se crean desde el cierre de
    caja y no se pueden agregar, modificar ni eliminar desde el admin.
    """
    list_display = ('fecha_cierre', 'caja_nombre', 'sucursal_nombre', 'cajero')
    list_filter = ('sucursal_nombre',)
    search_fields = ('caja_nombre', 'sucursal_nombre', 'cajero__username', 'cajero__first_name', 'cajero__last_name')
    date_hierarchy = 'fecha_cierre'
    inlines = [DetalleArqueoInline]

    def has_add_permission(self, request):
        """Los arqueos solo se crean desde el cierre de caja."""
        return False

    def has_change_permission(self, request, obj=None):
        """Los arqueos registrados no se modifican."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Los arqueos registrados no se eliminan."""
        return False
