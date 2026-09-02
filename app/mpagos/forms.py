"""
Módulo de formularios para la aplicación de Medios de Pago (mpagos).

Contiene los formularios MVT encargados de la validación de campos
y la construcción de widgets para la creación/edición de registros.
"""

from django import forms
from .models import MedioPago


class MedioPagoForm(forms.ModelForm):
    """
    Formulario MVT para la creación y edición de Medios de Pago.

    Mapea directamente contra el modelo MedioPago aplicando clases de CSS
    y restricciones para asegurar la entrada limpia de datos del cliente.
    """

    class Meta:
        """Vinculación del formulario con el modelo de base de datos."""
        model = MedioPago
        fields = ['tipo', 'nombre_titular', 'banco_emisor', 'numero_enmascarado', 'es_predeterminado']
        
        # Asignación de widgets e interactividad para las plantillas HTML
        widgets = {
            'tipo': forms.Select(attrs={
                'class': 'form-select',
                'aria-label': 'Seleccione el tipo de medio de pago'
            }),
            'nombre_titular': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ej. Juan Pérez'
            }),
            'banco_emisor': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ej. Banco Itaú / Continental'
            }),
            'numero_enmascarado': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ej. **** **** **** 4321 o Alias SIPAP'
            }),
            'es_predeterminado': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_numero_enmascarado(self):
        """
        Validación personalizada para garantizar que no se ingresen números de tarjeta planos.

        Returns:
            str: Número de cuenta o tarjeta validado.
        """
        # Extraer el valor ingresado por el usuario en el formulario
        numero = self.cleaned_data.get('numero_enmascarado')
        
        # Regla de seguridad: Si tiene formato numérico largo puro, advertir o enmascarar
        if numero and len(numero) == 16 and numero.isdigit():
            # Devuelve enmascarado preservando los últimos 4 dígitos
            return f"**** **** **** {numero[-4:]}"
            
        return numero