"""Registro de los modelos de clientes en el panel de administración."""

from django.contrib import admin
from .models import Cliente, UsuarioCliente

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    """Configuración del listado de clientes en el admin."""
    list_display = ('nombre_o_denominacion', 'documento', 'categoria', 'tipo_persona')

@admin.register(UsuarioCliente)
class UsuarioClienteAdmin(admin.ModelAdmin):
    """Configuración del listado de asociaciones usuario-cliente en el admin."""
    list_display = ('usuario', 'cliente', 'fecha_asociacion')