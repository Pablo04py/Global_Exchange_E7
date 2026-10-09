"""Formularios de la aplicación arqueos."""

from django import forms


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
