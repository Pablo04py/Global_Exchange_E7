"""Formularios de la aplicación arqueos."""

from django import forms
from django.contrib.auth import get_user_model


class CierreCajaForm(forms.Form):
    """Saldo físico declarado por el cajero, un campo por moneda de la caja.

    Es un arqueo ciego: el formulario no muestra el saldo registrado, solo
    pide lo que el cajero contó. Los campos se llaman `saldo_<MONEDA>`.
    """

    def __init__(self, *args, monedas, **kwargs):
        """Crea un campo de saldo por cada moneda de la caja.

        Args:
            monedas: Códigos de las monedas a declarar, ej. `['PYG', 'USD']`.
        """
        super().__init__(*args, **kwargs)
        self.monedas = list(monedas)
        for moneda in self.monedas:
            self.fields[f'saldo_{moneda}'] = forms.DecimalField(
                label=moneda,
                min_value=0,
                max_digits=18,
                decimal_places=2,
                widget=forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            )

    def saldos_declarados(self):
        """Devuelve los saldos válidos por moneda.

        Returns:
            dict[str, Decimal]: Saldo declarado por código de moneda.
        """
        return {moneda: self.cleaned_data[f'saldo_{moneda}'] for moneda in self.monedas}


class _CajeroChoiceField(forms.ModelChoiceField):
    """Muestra al cajero por su nombre completo o, si no lo tiene, por su `username`."""
    def label_from_instance(self, obj):
        """Devuelve el nombre completo del cajero o su `username`."""
        return obj.get_full_name() or obj.username


class FiltroReporteForm(forms.Form):
    """Filtros del reporte de auditoría de caja (vía GET, solo lectura).

    Las opciones de sucursal y cajero salen de los arqueos registrados, de
    modo que el reporte no depende de los modelos de sucursal o caja de otras
    historias. Todos los campos son opcionales.
    """
    NIVEL_SIN = 'SIN'
    NIVEL_SOBRANTE = 'SOBRANTE'
    NIVEL_FALTANTE = 'FALTANTE'
    NIVELES = [
        ('', 'Todos'),
        (NIVEL_SIN, 'Sin discrepancia'),
        (NIVEL_SOBRANTE, 'Con sobrante'),
        (NIVEL_FALTANTE, 'Con faltante'),
    ]

    fecha_desde = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    fecha_hasta = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    sucursal = forms.ChoiceField(required=False)
    cajero = _CajeroChoiceField(queryset=None, required=False, empty_label='Todos')
    nivel = forms.ChoiceField(choices=NIVELES, required=False, label='Nivel de discrepancia')

    def __init__(self, *args, arqueos, **kwargs):
        """Carga las opciones de sucursal y cajero a partir de los arqueos registrados.

        Args:
            arqueos: QuerySet de `ArqueoCaja` disponibles para el reporte.
        """
        super().__init__(*args, **kwargs)
        sucursales = (
            arqueos.exclude(sucursal_nombre='').order_by('sucursal_nombre')
            .values_list('sucursal_nombre', flat=True).distinct()
        )
        self.fields['sucursal'].choices = [('', 'Todas')] + [(s, s) for s in sucursales]
        self.fields['cajero'].queryset = get_user_model().objects.filter(arqueos__in=arqueos).distinct()

    def clean(self):
        """Valida que la fecha "desde" no sea posterior a la fecha "hasta".

        Si el rango es inválido se descartan ambas fechas para no filtrar a medias.

        Returns:
            dict: Datos limpios del formulario.
        """
        cleaned_data = super().clean()
        desde, hasta = cleaned_data.get('fecha_desde'), cleaned_data.get('fecha_hasta')
        if desde and hasta and desde > hasta:
            self.add_error('fecha_hasta', 'Debe ser mayor o igual que la fecha inicial.')
            cleaned_data.pop('fecha_desde', None)
        return cleaned_data

    def filtrar(self, arqueos):
        """Aplica los filtros con valor válido.

        Args:
            arqueos: QuerySet devuelto por `reportes.arqueos_para_reporte`.

        Returns:
            QuerySet: Arqueos filtrados.
        """
        datos = getattr(self, 'cleaned_data', {})
        if datos.get('fecha_desde'):
            arqueos = arqueos.filter(fecha_cierre__date__gte=datos['fecha_desde'])
        if datos.get('fecha_hasta'):
            arqueos = arqueos.filter(fecha_cierre__date__lte=datos['fecha_hasta'])
        if datos.get('sucursal'):
            arqueos = arqueos.filter(sucursal_nombre=datos['sucursal'])
        if datos.get('cajero'):
            arqueos = arqueos.filter(cajero=datos['cajero'])
        nivel = datos.get('nivel')
        if nivel == self.NIVEL_SIN:
            arqueos = arqueos.filter(tiene_faltante=False, tiene_sobrante=False)
        elif nivel == self.NIVEL_SOBRANTE:
            arqueos = arqueos.filter(tiene_sobrante=True)
        elif nivel == self.NIVEL_FALTANTE:
            arqueos = arqueos.filter(tiene_faltante=True)
        return arqueos
