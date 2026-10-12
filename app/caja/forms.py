from django import forms
from django.contrib.auth import get_user_model
from .models import Caja, SesionCaja, EstadoCaja, EstadoSesionCaja
from operaciones.models import Moneda

User = get_user_model()


class CajeroChoiceField(forms.ModelChoiceField):
    """
    Campo personalizado para mostrar el nombre completo o email del cajero,
    evitando mostrar los hashes generados por Keycloak.
    """
    def label_from_instance(self, obj):
        return obj.get_full_name() or obj.email or obj.username


class AsignarCajeroForm(forms.ModelForm):
    caja = forms.ModelChoiceField(
        queryset=Caja.objects.filter(estado=EstadoCaja.DISPONIBLE, activa=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Caja Registradora"
    )
    cajero = CajeroChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Cajero a Asignar"
    )

    class Meta:
        model = SesionCaja
        fields = ['caja', 'cajero']

    def clean_cajero(self):
        cajero = self.cleaned_data.get('cajero')
        sesion_pendiente = SesionCaja.objects.filter(
            cajero=cajero,
            estado__in=[EstadoSesionCaja.ASIGNADA, EstadoSesionCaja.ABIERTA]
        ).exists()

        if sesion_pendiente:
            raise forms.ValidationError("Este cajero ya tiene una caja asignada o abierta actualmente.")
        return cajero


class AperturaCajaForm(forms.Form):
    """
    Formulario dinámico que genera un campo de entrada para cada moneda habilitada en la base de datos.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        monedas = Moneda.objects.filter(habilitada=True)
        for moneda in monedas:
            self.fields[f'monto_{moneda.codigo.lower()}'] = forms.DecimalField(
                max_digits=15,
                decimal_places=2,
                min_value=0,
                initial=0.00,
                label=f"Fondo Inicial en {moneda.nombre} ({moneda.codigo})",
                widget=forms.NumberInput(attrs={
                    'class': 'form-control', 
                    'step': '0.01', 
                    'placeholder': '0.00'
                })
            )