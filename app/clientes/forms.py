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

    def clean(self):
        cleaned_data = super().clean()
        usuario = cleaned_data.get('usuario')
        cliente = cleaned_data.get('cliente')

        if usuario and cliente:
            instancia_temp = UsuarioCliente(usuario=usuario, cliente=cliente)
            instancia_temp.clean()
        return cleaned_data