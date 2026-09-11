from django import forms
from .models import Moneda, TasaDeCambio


class MonedaForm(forms.ModelForm):
    class Meta:
        model = Moneda
        fields = ['codigo', 'nombre', 'habilitada']



class TasaDeCambioForm(forms.ModelForm):
    class Meta:
        model = TasaDeCambio
        fields = ['moneda', 'tasa_base', 'margen_compra', 'margen_venta']