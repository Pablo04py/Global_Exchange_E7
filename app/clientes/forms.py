from django import forms
from .models import Cliente, UsuarioCliente

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['tipo_persona', 'nombre_o_denominacion', 'documento', 'categoria']

class AsignacionForm(forms.ModelForm):
    class Meta:
        model = UsuarioCliente
        fields = ['usuario', 'cliente']