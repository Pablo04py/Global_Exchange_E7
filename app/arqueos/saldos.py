"""Saldo registrado de un turno de caja para el arqueo (SCRUM-40).

Combina las dos fuentes que hoy existen en la app `caja`:

- SCRUM-37 (apertura): el fondo inicial por moneda queda en `SaldoInicialCaja`
  (y el de guaraníes en `SesionCaja.monto_inicial`).
- SCRUM-39 (operación de cajeros): las entradas y salidas de efectivo del
  turno quedan en `MovimientoCaja`; `caja.services.saldo_por_moneda` las suma.

La apertura todavía no registra un `MovimientoCaja` de tipo `APERTURA`, por lo
que `saldo_por_moneda` no incluye el fondo inicial. Esta función lo suma desde
`SaldoInicialCaja`, pero solo si el turno no tiene movimientos de apertura:
cuando la apertura empiece a registrarlos, deja de sumarlo para no contarlo
dos veces.

Es la función que usa el arqueo por defecto (setting `ARQUEO_FUNCION_SALDO`).
"""

from decimal import Decimal

from caja.models import TipoMovimiento
from caja.services import MONEDA_LOCAL, saldo_por_moneda

CERO = Decimal('0')


def saldo_inicial(turno):
    """Devuelve el fondo inicial del turno por moneda.

    El guaraní siempre se incluye: si la apertura no lo cargó como moneda,
    se toma de `monto_inicial` del turno.

    Args:
        turno: `SesionCaja` abierta.

    Returns:
        dict[str, Decimal]: Fondo inicial por código de moneda.
    """
    inicial = {s.moneda.codigo.upper(): s.monto for s in turno.saldos_iniciales.select_related('moneda')}
    inicial.setdefault(MONEDA_LOCAL, turno.monto_inicial or CERO)
    return inicial


def saldo_registrado(turno):
    """Devuelve el efectivo que debería haber en la caja, por moneda.

    `saldo registrado = fondo inicial + entradas - salidas del turno`. Incluye
    todas las monedas abiertas o movidas en el turno (aunque su saldo sea 0)
    y siempre el guaraní, para que el cajero declare cada una.

    Args:
        turno: `SesionCaja` abierta.

    Returns:
        dict[str, Decimal]: Saldo registrado por código de moneda.
    """
    saldo = {moneda: Decimal(monto) for moneda, monto in saldo_por_moneda(turno).items()}
    tiene_apertura_registrada = turno.movimientos.filter(tipo=TipoMovimiento.APERTURA).exists()

    for moneda, monto in saldo_inicial(turno).items():
        base = saldo.get(moneda, CERO)
        saldo[moneda] = base if tiene_apertura_registrada else base + Decimal(monto)
    return saldo
