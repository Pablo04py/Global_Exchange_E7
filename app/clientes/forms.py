from django import forms
from .models import Cliente, UsuarioCliente
class ClienteFisicaForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre_o_denominacion', 'documento']
class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['tipo_persona', 'nombre_o_denominacion', 'documento', 'categoria']

class AsignacionForm(forms.ModelForm):
    class Meta:
        model = UsuarioCliente
        fields = ['usuario', 'cliente']
