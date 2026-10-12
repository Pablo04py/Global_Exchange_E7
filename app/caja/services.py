from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum

from .models import (
    EstadoSesionCaja, MovimientoCaja, SentidoMovimiento, TipoMovimiento,
)

MONEDA_LOCAL = 'PYG'
CERO = Decimal('0')


def saldo_por_moneda(sesion):
    """Devuelve {'PYG': Decimal, 'USD': Decimal, ...} con el efectivo actual de la sesión."""
    filas = sesion.movimientos.values('moneda').annotate(
        entradas=Sum('monto', filter=Q(sentido=SentidoMovimiento.ENTRADA)),
        salidas=Sum('monto', filter=Q(sentido=SentidoMovimiento.SALIDA)),
    )
    return {f['moneda']: (f['entradas'] or CERO) - (f['salidas'] or CERO) for f in filas}


@transaction.atomic
def registrar_movimiento_transaccion(sesion, transaccion):
    """Registra en la caja el efectivo que entra y sale por una transacción.

    - La divisa extranjera siempre es billete físico: entra o sale de la caja.
    - El guaraní solo mueve la caja si el medio de pago es EFECTIVO. Con tarjeta
      o transferencia el dinero no pasa por el cajón.
    - Es idempotente: si la transacción ya tiene movimientos, no duplica.
    - Lanza ValidationError si no hay stock suficiente de lo que se entrega.
    """
    if sesion.estado != EstadoSesionCaja.ABIERTA:
        raise ValidationError("La sesión de caja no está abierta.")

    existentes = list(sesion.movimientos.filter(transaccion=transaccion))
    if existentes:
        return existentes

    en_efectivo = transaccion.medio_pago.tipo == 'EFECTIVO'
    patas = [
        (SentidoMovimiento.ENTRADA, transaccion.moneda_pagada, transaccion.monto_pagado),
        (SentidoMovimiento.SALIDA, transaccion.moneda_recibida, transaccion.monto_recibido),
    ]

    creados = []
    for sentido, moneda, monto in patas:
        if moneda == MONEDA_LOCAL and not en_efectivo:
            continue  # el guaraní viajó por tarjeta/transferencia, no por el cajón

        if sentido == SentidoMovimiento.SALIDA:
            disponible = saldo_por_moneda(sesion).get(moneda, CERO)
            if disponible < monto:
                raise ValidationError(
                    f"Stock insuficiente de {moneda} en caja: hay {disponible} y se necesitan {monto}."
                )

        creados.append(MovimientoCaja.objects.create(
            sesion=sesion, transaccion=transaccion, tipo=TipoMovimiento.OPERACION,
            sentido=sentido, moneda=moneda, monto=monto,
            justificacion=f"Operación {transaccion.pk}",
        ))
    return creados