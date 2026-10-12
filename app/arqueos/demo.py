"""Saldo registrado de demostración para probar el cierre de caja (solo desarrollo).

La función real de saldo registrado pertenece a otra historia. Mientras no
exista, se puede probar el cierre en el navegador apuntando el setting
`ARQUEO_FUNCION_SALDO` a esta función desde el archivo `.env`:

    ARQUEO_FUNCION_SALDO=arqueos.demo.saldo_de_demostracion

y creando un turno abierto con el comando `preparar_demo_cierre`. Cuando la
función real esté disponible, basta con quitar esa línea del `.env`.
"""

from decimal import Decimal

from django.conf import settings

from .integracion import ModuloCajaNoDisponible

SALDO_USD_DEMO = Decimal('1000')
SALDO_PYG_POR_DEFECTO = Decimal('5000000')


def saldo_de_demostracion(turno):
    """Devuelve un saldo registrado de ejemplo para el turno.

    Usa el monto inicial del turno como saldo en guaraníes (o 5.000.000 si no
    tiene) y 1.000 USD fijos.

    Args:
        turno: Turno de caja abierto.

    Returns:
        dict[str, Decimal]: Saldo de ejemplo por moneda.

    Raises:
        ModuloCajaNoDisponible: Si se usa con `DEBUG=False`.
    """
    if not settings.DEBUG:
        raise ModuloCajaNoDisponible("El saldo de demostración solo puede usarse con DEBUG=True.")
    monto_inicial = getattr(turno, 'monto_inicial', None) or SALDO_PYG_POR_DEFECTO
    return {'PYG': Decimal(monto_inicial), 'USD': SALDO_USD_DEMO}
