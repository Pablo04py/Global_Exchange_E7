"""Puente entre operaciones y el módulo de caja.

Es lo único que `operaciones` conoce de `caja`. Si cambian los modelos de
caja, solo se ajusta este archivo.
"""

from caja.models import EstadoSesionCaja, SesionCaja
from caja.services import registrar_movimiento_transaccion, saldo_por_moneda


class SesionCajaNoAbierta(Exception):
    """El cajero no tiene una sesión de caja en estado ABIERTA."""


def obtener_sesion_abierta(cajero, bloquear=False):
    """Devuelve la sesión ABIERTA del cajero o lanza SesionCajaNoAbierta.

    Args:
        cajero: Usuario con rol Cajero.
        bloquear: Si es True usa `select_for_update` sobre la sesión, para que
            un cierre/arqueo concurrente espere a que termine la operación.
            Solo válido dentro de una transacción atómica.
    """
    qs = (
        SesionCaja.objects
        .select_related('caja')
        .filter(cajero=cajero, estado=EstadoSesionCaja.ABIERTA)
        .order_by('-fecha_apertura')
    )
    if bloquear:
        qs = qs.select_for_update(of=('self',))

    sesion = qs.first()
    if sesion is None:
        raise SesionCajaNoAbierta("Debe tener una sesión de caja abierta para operar.")
    return sesion


def registrar_movimiento(sesion, transaccion):
    """Registra en la caja el movimiento de una transacción confirmada.

    Contrato que debe cumplir `caja.services.registrar_movimiento_transaccion`:
    - Entra `transaccion.monto_pagado` en `transaccion.moneda_pagada`.
    - Sale `transaccion.monto_recibido` en `transaccion.moneda_recibida`.
    - Lanza ValidationError si no hay stock suficiente de lo que se entrega.
    - Es idempotente por transacción (no duplica el movimiento).
    """
    return registrar_movimiento_transaccion(sesion, transaccion)


def obtener_saldos(sesion):
    """Saldo de efectivo por moneda de la sesión: {'PYG': ..., 'USD': ...}."""
    return saldo_por_moneda(sesion)