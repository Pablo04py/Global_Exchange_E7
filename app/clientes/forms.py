"""Formularios de la aplicación clientes."""

from django import forms
from .models import Cliente, UsuarioCliente
class ClienteFisicaForm(forms.ModelForm):
    """Formulario simplificado para que un usuario se registre como cliente persona física."""
    class Meta:
        """Campos: nombre y documento."""
        model = Cliente
        fields = ['nombre_o_denominacion', 'documento']
class ClienteForm(forms.ModelForm):
    """Formulario completo de alta y edición de clientes (uso del administrador)."""
    class Meta:
        """Campos: tipo de persona, nombre o denominación, documento y categoría."""
        model = Cliente
        fields = ['tipo_persona', 'nombre_o_denominacion', 'documento', 'categoria']

class AsignacionForm(forms.ModelForm):
    """Formulario para asociar un usuario del sistema con un cliente."""
    class Meta:
        """Campos: usuario y cliente."""
        model = UsuarioCliente
        fields = ['usuario', 'cliente']
