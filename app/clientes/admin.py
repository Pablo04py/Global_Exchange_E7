from django.contrib import admin
from .models import Cliente, UsuarioCliente

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre_o_denominacion', 'documento', 'categoria', 'tipo_persona')

@admin.register(UsuarioCliente)
class UsuarioClienteAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'cliente', 'fecha_asociacion')