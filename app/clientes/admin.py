"""
Configuración del panel de administración estándar de Django para Clientes.

Permite administrar clientes, visualizar relaciones de manera tabular (inlines)
y realizar búsquedas avanzadas.
"""

from django.contrib import admin
from .models import Cliente, UsuarioCliente


class UsuarioClienteInline(admin.TabularInline):
    """Permite visualizar y asociar usuarios directamente dentro de la vista de un Cliente."""

    model = UsuarioCliente
    # Muestra un espacio en blanco adicional para cargar un usuario
    extra = 1


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    """Configuración del panel administrativo para el modelo `Cliente`."""

    # Configuración de columnas visibles en las tablas del Admin
    list_display = ('nombre_o_denominacion', 'documento', 'tipo_persona', 'categoria', 'fecha_registro')
    list_filter = ('tipo_persona', 'categoria')
    search_fields = ('nombre_o_denominacion', 'documento')
    # Muestra el inline de usuarios asociados al pie de la ficha del cliente
    inlines = [UsuarioClienteInline]


@admin.register(UsuarioCliente)
class UsuarioClienteAdmin(admin.ModelAdmin):
    """Configuración del panel administrativo para la tabla intermedia `UsuarioCliente`."""

    list_display = ('usuario', 'cliente', 'fecha_asociacion')
    list_filter = ('cliente__tipo_persona',)
    # Permite buscar relaciones cruzadas por datos de usuario o de cliente
    search_fields = ('usuario__username', 'usuario__email', 'cliente__nombre_o_denominacion', 'cliente__documento')