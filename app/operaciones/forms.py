"""Formularios de la aplicación operaciones."""

from django import forms
from django.contrib.auth import get_user_model

from mpagos.models import MedioPago
from .models import Moneda, TasaDeCambio, Transaccion

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


class _MedioPagoChoiceField(forms.ModelChoiceField):
    """Muestra el medio de pago con su número enmascarado (ej. `Tarjeta **** 1234`)."""
    def label_from_instance(self, obj):
        """Devuelve `tipo número_enmascarado`."""
        return f"{obj.get_tipo_display()} {obj.numero_enmascarado}"


class _UsuarioChoiceField(forms.ModelChoiceField):
    """Muestra a un usuario (cajero u operador) por su nombre completo o, si no lo tiene, por su `username`."""
    def label_from_instance(self, obj):
        """Devuelve el nombre completo del usuario o su `username`."""
        return obj.get_full_name() or obj.username


class FiltroHistorialForm(forms.Form):
    """Filtros del historial de transacciones del cliente (solo lectura, vía GET).

    Las opciones de moneda, medio de pago, cajero y "operado por" se
    construyen a partir de las transacciones del cliente activo, de modo que
    un identificador ajeno enviado en la URL no es una opción válida.

    Todos los campos son opcionales; los que no se completan no filtran.
    """
    SI_NO_CHOICES = [('', 'Todas'), ('si', 'Sí'), ('no', 'No')]

    fecha_desde = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    fecha_hasta = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    hora_desde = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time'}))
    hora_hasta = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time'}))
    tipo = forms.ChoiceField(choices=[('', 'Todos')] + Transaccion.Tipo.choices, required=False)
    moneda = forms.ModelChoiceField(queryset=Moneda.objects.none(), required=False, empty_label='Todas')
    medio_pago = _MedioPagoChoiceField(queryset=MedioPago.objects.none(), required=False, empty_label='Todos')
    monto_pagado_min = forms.DecimalField(required=False, min_value=0)
    monto_pagado_max = forms.DecimalField(required=False, min_value=0)
    monto_recibido_min = forms.DecimalField(required=False, min_value=0)
    monto_recibido_max = forms.DecimalField(required=False, min_value=0)
    facturada = forms.ChoiceField(choices=SI_NO_CHOICES, required=False)
    dispositivo = forms.ChoiceField(choices=[('', 'Todos')] + Transaccion.Dispositivo.choices, required=False)
    cajero = _UsuarioChoiceField(queryset=get_user_model().objects.none(), required=False, empty_label='Todos')
    operado_por = _UsuarioChoiceField(queryset=get_user_model().objects.none(), required=False, empty_label='Todos')
    estado = forms.ChoiceField(choices=[('', 'Todos')] + Transaccion.Estado.choices, required=False)

    # (campo "desde", campo "hasta") que deben formar un rango válido
    RANGOS = [
        ('fecha_desde', 'fecha_hasta'),
        ('hora_desde', 'hora_hasta'),
        ('monto_pagado_min', 'monto_pagado_max'),
        ('monto_recibido_min', 'monto_recibido_max'),
    ]

    def __init__(self, *args, transacciones, **kwargs):
        """Limita las opciones del formulario a las transacciones del cliente activo.

        Args:
            transacciones: QuerySet de `Transaccion` del cliente activo.
        """
        super().__init__(*args, **kwargs)
        Usuario = get_user_model()
        self.fields['moneda'].queryset = Moneda.objects.filter(transacciones__in=transacciones).distinct()
        self.fields['medio_pago'].queryset = MedioPago.objects.filter(transacciones__in=transacciones).distinct()
        self.fields['cajero'].queryset = Usuario.objects.filter(transacciones_atendidas__in=transacciones).distinct()
        self.fields['operado_por'].queryset = Usuario.objects.filter(
            transacciones_realizadas__in=transacciones
        ).distinct()

    def clean(self):
        """Valida que en cada rango el valor "desde" no supere al "hasta".

        Si un rango es inválido se descartan ambos extremos, para que ese
        rango no filtre de forma parcial.

        Returns:
            dict: Datos limpios del formulario.
        """
        cleaned_data = super().clean()
        for campo_desde, campo_hasta in self.RANGOS:
            desde = cleaned_data.get(campo_desde)
            hasta = cleaned_data.get(campo_hasta)
            if desde is not None and hasta is not None and desde > hasta:
                self.add_error(campo_hasta, 'Debe ser mayor o igual que el valor inicial.')
                cleaned_data.pop(campo_desde, None)
        return cleaned_data

    def filtrar(self, transacciones):
        """Aplica al QuerySet los filtros que tengan un valor válido.

        Se usa `cleaned_data`, por lo que un campo con error se ignora y no
        amplía ni altera el conjunto de transacciones del cliente activo.

        Args:
            transacciones: QuerySet de `Transaccion` del cliente activo.

        Returns:
            QuerySet: Transacciones filtradas.
        """
        datos = getattr(self, 'cleaned_data', {})
        # campo del formulario -> lookup del ORM
        lookups = {
            'fecha_desde': 'fecha__date__gte',
            'fecha_hasta': 'fecha__date__lte',
            'hora_desde': 'fecha__time__gte',
            'hora_hasta': 'fecha__time__lte',
            'tipo': 'tipo',
            'moneda': 'moneda',
            'medio_pago': 'medio_pago',
            'monto_pagado_min': 'monto_pagado__gte',
            'monto_pagado_max': 'monto_pagado__lte',
            'monto_recibido_min': 'monto_recibido__gte',
            'monto_recibido_max': 'monto_recibido__lte',
            'dispositivo': 'dispositivo',
            'cajero': 'cajero',
            'operado_por': 'usuario',
            'estado': 'estado',
        }
        filtros = {
            lookup: datos[campo]
            for campo, lookup in lookups.items()
            if datos.get(campo) not in (None, '')
        }
        if datos.get('facturada'):
            filtros['facturada'] = datos['facturada'] == 'si'
        return transacciones.filter(**filtros)
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
