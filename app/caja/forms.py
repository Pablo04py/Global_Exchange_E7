from django import forms

from django import forms
from django.contrib.auth import get_user_model
from .models import Caja, SesionCaja, EstadoCaja, EstadoSesionCaja

User = get_user_model()


class AsignarCajeroForm(forms.ModelForm):
    caja = forms.ModelChoiceField(
        queryset=Caja.objects.filter(estado=EstadoCaja.DISPONIBLE, activa=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Caja Registradora"
    )
    cajero = forms.ModelChoiceField(
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