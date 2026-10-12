"""Saldo registrado de un turno de caja para el arqueo (SCRUM-40).

Calcula el saldo esperado de la caja sumando todas las entradas y salidas
registradas en el libro mayor (incluyendo la apertura y las operaciones del turno)
a través de `caja.services.saldo_por_moneda`.
"""

from decimal import Decimal
from caja.services import saldo_por_moneda

CERO = Decimal('0')


def saldo_registrado(turno):
    """Devuelve el efectivo que debería haber en la caja, por moneda.

    Obtiene el saldo dinámico directamente del libro mayor de movimientos,
    garantizando que la apertura, operaciones y transferencias se reflejen
    correctamente sin desincronizarse.

    Args:
        turno: `SesionCaja` abierta.

    Returns:
        dict[str, Decimal]: Saldo registrado por código de moneda.
    """
    saldos = saldo_por_moneda(turno)
    return {moneda: Decimal(monto) for moneda, monto in saldos.items()}