"""Formularios de la aplicación clientes."""

from django import forms
from .models import Cliente, UsuarioCliente
from django.contrib.auth import get_user_model


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
        fields = ['tipo_persona', 'nombre_o_denominacion', 'documento', 'digito_verificador', 'categoria']
        labels = {'tipo_persona': 'Tipo de persona', 'nombre_o_denominacion': 'Nombre / Razón social', 'documento': 'CI / RUC', 'digito_verificador': 'Dígito verificador', 'categoria': 'Categoría'}
        help_texts = {'documento': ('Ingrese la CI para persona física o el RUC sin dígito verificador para persona jurídica.'),'digito_verificador': ('Obligatorio únicamente para persona jurídica.'),}

    def clean(self):
        cleaned_data = super().clean()

        tipo_persona = cleaned_data.get('tipo_persona')
        dv = cleaned_data.get('digito_verificador')

        if tipo_persona == Cliente.TipoPersona.JURIDICA and not dv:
            self.add_error(
                'digito_verificador',
                'El dígito verificador es obligatorio para una persona jurídica.'
            )

        if tipo_persona == Cliente.TipoPersona.FISICA:
            cleaned_data['digito_verificador'] = None

        return cleaned_data

Usuario = get_user_model()


class UsuarioLegibleChoiceField(forms.ModelChoiceField):
    """Muestra el nombre completo y correo del usuario."""

    def label_from_instance(self, usuario):
        nombre = usuario.get_full_name().strip()
        correo = (usuario.email or "").strip()

        if nombre and correo:
            return f"{nombre} ({correo})"

        return nombre or correo or usuario.username

class AsignacionForm(forms.ModelForm):
    """Formulario para asociar un usuario del sistema con un cliente."""

    usuario = UsuarioLegibleChoiceField(queryset=Usuario.objects.order_by('first_name', 'last_name', 'email'), label='Usuario', empty_label='Seleccione un usuario')
    
    class Meta:
        """Campos: usuario y cliente."""
        model = UsuarioCliente
        fields = ['usuario', 'cliente']
