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
    """

    class Meta:
        model = MedioPago
        # Usamos numero_enmascarado que es el campo real del modelo
        fields = ['tipo', 'nombre_titular', 'banco_emisor', 'numero_enmascarado', 'es_predeterminado']
        labels = {
            'tipo': 'Tipo de Medio de Pago',
            'nombre_titular': 'Nombre del Titular',
            'banco_emisor': 'Banco o Entidad Emisora',
            'numero_enmascarado': 'Número de Tarjeta / Cuenta / Teléfono',
            'es_predeterminado': 'Marcar como Medio de Pago Predeterminado',
        }
        
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
                'placeholder': 'Ej. 4532xxxxxx1234 o Alias SIPAP / Cédula'
            }),
            'es_predeterminado': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_numero_enmascarado(self):
        """
        Validación personalizada para garantizar que no se ingresen números de tarjeta planos.
        """
        numero = self.cleaned_data.get('numero_enmascarado')
        
        if numero:
            numero_limpio = numero.replace(" ", "").replace("-", "")
            if len(numero_limpio) == 16 and numero_limpio.isdigit():
                return f"**** **** **** {numero_limpio[-4:]}"
            
        return numero