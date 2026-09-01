from django.contrib import admin
from .models import Cliente, UsuarioCliente

class UsuarioClienteInline(admin.TabularInline):
    model = UsuarioCliente
    extra = 1

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre_o_denominacion', 'documento', 'tipo_persona', 'categoria', 'fecha_registro')
    list_filter = ('tipo_persona', 'categoria')
    search_fields = ('nombre_o_denominacion', 'documento')
    inlines = [UsuarioClienteInline]

@admin.register(UsuarioCliente)
class UsuarioClienteAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'cliente', 'fecha_asociacion')
    list_filter = ('cliente__tipo_persona',)
    search_fields = ('usuario__username', 'usuario__email', 'cliente__nombre_o_denominacion', 'cliente__documento')