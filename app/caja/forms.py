from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model

from .models import Caja, SesionCaja, EstadoCaja, EstadoSesionCaja
from operaciones.models import Moneda

User = get_user_model()

ESTADOS_ACTIVOS = [EstadoSesionCaja.ASIGNADA, EstadoSesionCaja.ABIERTA]


class CajeroChoiceField(forms.ModelChoiceField):
    """
    Campo personalizado para mostrar el nombre completo o email del cajero,
    evitando mostrar los hashes generados por Keycloak.
    """
    def label_from_instance(self, obj):
        return obj.get_full_name() or obj.email or obj.username

class CajaForm(forms.ModelForm):
    """Formulario para registrar una nueva caja."""

    class Meta:
        model = Caja
        fields = ['nombre', 'codigo']

        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej.: Caja Principal',
            }),
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej.: CAJA-01',
            }),
        }

        labels = {
            'nombre': 'Nombre de la caja',
            'codigo': 'Código de la caja',
        }

        help_texts = {
            'nombre': 'Nombre descriptivo para identificar la caja.',
            'codigo': 'Código único utilizado internamente por el sistema.',
        }

    def clean_codigo(self):
        """Normaliza el código de la caja a mayúsculas."""
        codigo = self.cleaned_data['codigo'].strip().upper()
        return codigo

class AsignarCajeroForm(forms.ModelForm):
    caja = forms.ModelChoiceField(
        queryset=Caja.objects.filter(estado=EstadoCaja.DISPONIBLE, activa=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Caja Registradora"
    )
    cajero = CajeroChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Cajero a Asignar"
    )

    class Meta:
        model = SesionCaja
        fields = ['caja', 'cajero']

    def clean_caja(self):
        caja = self.cleaned_data.get('caja')
        if caja and SesionCaja.objects.filter(caja=caja, estado__in=ESTADOS_ACTIVOS).exists():
            raise forms.ValidationError("Esta caja ya está asignada a otro cajero.")
        return caja

    def clean_cajero(self):
        cajero = self.cleaned_data.get('cajero')
        if cajero and SesionCaja.objects.filter(cajero=cajero, estado__in=ESTADOS_ACTIVOS).exists():
            raise forms.ValidationError("Este cajero ya tiene una caja asignada o abierta actualmente.")
        return cajero


class MontosPorMonedaForm(forms.Form):
    """
    Base dinámica: un campo numérico `monto_<codigo>` por cada moneda habilitada
    (más las monedas extra que se indiquen, por ejemplo las que ya tienen saldo en caja).
    """
    etiqueta = "{nombre} ({codigo})"
    valor_inicial = None

    def __init__(self, *args, codigos_extra=(), **kwargs):
        super().__init__(*args, **kwargs)

        nombres = {
            m.codigo.upper(): m.nombre
            for m in Moneda.objects.filter(habilitada=True).order_by('codigo')
        }
        for codigo in codigos_extra:
            nombres.setdefault(codigo.upper(), codigo.upper())

        self.campos_moneda = {}  # {'monto_pyg': 'PYG', ...}
        for codigo, nombre in nombres.items():
            campo = f'monto_{codigo.lower()}'
            self.fields[campo] = forms.DecimalField(
                max_digits=15,
                decimal_places=2,
                min_value=0,
                initial=self.valor_inicial,
                label=self.etiqueta.format(nombre=nombre, codigo=codigo),
                widget=forms.NumberInput(attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'placeholder': '0.00',
                })
            )
            self.campos_moneda[campo] = codigo

    def montos_por_moneda(self):
        """Devuelve {'PYG': Decimal, 'USD': Decimal, ...} con lo ingresado."""
        return {
            codigo: self.cleaned_data.get(campo) or Decimal('0')
            for campo, codigo in self.campos_moneda.items()
        }


class AperturaCajaForm(MontosPorMonedaForm):
    etiqueta = "Fondo Inicial en {nombre} ({codigo})"
    valor_inicial = Decimal('0.00')
