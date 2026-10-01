"""Formularios de la aplicación operaciones."""

from django import forms
from .models import Moneda, TasaDeCambio, Transaccion, ConfiguracionComision
from mpagos.models import MedioPago

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

class OperacionForm(forms.Form):

    tipo_operacion = forms.ChoiceField(
        choices=Transaccion.TipoOperacion.choices,
        label="Tipo de operación"
    )

    moneda = forms.ModelChoiceField(
        queryset=Moneda.objects.none(),
        label="Moneda",
        empty_label="Seleccione una moneda"
    )

    monto = forms.DecimalField(
        max_digits=18,
        decimal_places=4,
        min_value=0.0001,
        label="Monto"
    )

    medio_pago = forms.ModelChoiceField(
        queryset=MedioPago.objects.none(),
        label="Medio de pago",
        empty_label="Seleccione un medio de pago"
    )

    tasa_id_simulada = forms.UUIDField(
        required=False,
        widget=forms.HiddenInput()
    )

    def __init__(self, *args, cliente=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['moneda'].queryset = (
            Moneda.objects
            .filter(habilitada=True)
            .distinct()
        )

        if cliente:
            self.fields['medio_pago'].queryset = (
                MedioPago.objects
                .filter(
                    cliente=cliente,
                    activo=True
                )
                .order_by(
                    '-es_predeterminado',
                    '-creado_en'
                )
            )