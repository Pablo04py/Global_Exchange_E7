"""Formularios de la aplicación operaciones."""

from django import forms
from .models import Moneda, TasaDeCambio


class MonedaForm(forms.ModelForm):
    """Formulario de alta y edición de monedas."""
    class Meta:
        """Campos: código ISO 4217, nombre y si está habilitada."""
        model = Moneda
        fields = ['codigo', 'nombre', 'habilitada']



class TasaDeCambioForm(forms.ModelForm):
    """Formulario para registrar una nueva tasa de cambio de una moneda."""
    class Meta:
        """Campos: moneda, tasa base, margen de compra y margen de venta."""
        model = TasaDeCambio
        fields = ['moneda', 'tasa_base', 'margen_compra', 'margen_venta']