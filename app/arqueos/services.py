"""Lógica de negocio del cierre de caja y arqueo (SCRUM-40)."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from . import integracion
from .models import ArqueoCaja, DetalleArqueo


def calcular_resultado(saldo_registrado, saldo_declarado):
    """Compara el saldo declarado por el cajero con el registrado por el sistema.

    Args:
        saldo_registrado: Saldo que el sistema esperaba en la caja.
        saldo_declarado: Saldo físico contado por el cajero.

    Returns:
        tuple[Decimal, str]: La diferencia (`declarado - registrado`) y el
        resultado: `CUADRA` si es cero, `SOBRANTE` si es positiva y
        `FALTANTE` si es negativa.
    """
    diferencia = Decimal(saldo_declarado) - Decimal(saldo_registrado)
    if diferencia > 0:
        return diferencia, DetalleArqueo.Resultado.SOBRANTE
    if diferencia < 0:
        return diferencia, DetalleArqueo.Resultado.FALTANTE
    return diferencia, DetalleArqueo.Resultado.CUADRA


@transaction.atomic
def registrar_cierre(cajero, saldos_declarados):
    """Cierra la caja abierta del cajero, registra el arqueo y bloquea la caja.

    Todo ocurre en una única transacción de base de datos: si algo falla, no
    queda ni el arqueo ni el bloqueo a medias. La fila de la caja se bloquea
    (`SELECT ... FOR UPDATE`) para que dos cierres simultáneos no se registren
    dos veces.

    Args:
        cajero: Usuario que cierra su caja.
        saldos_declarados: Saldo físico por código de moneda,
            ej. `{'PYG': Decimal('5740000'), 'USD': Decimal('880')}`.

    Returns:
        ArqueoCaja: El arqueo registrado, con sus detalles por moneda.

    Raises:
        ValidationError: Si el cajero no tiene una caja abierta o las monedas
            declaradas no coinciden con las del saldo registrado.
        integracion.ModuloCajaNoDisponible: Si el módulo de caja no está disponible.
    """
    caja = integracion.obtener_caja_abierta(cajero, bloquear_fila=True)
    if caja is None:
        raise ValidationError("No tenés una caja abierta asignada para cerrar.")

    saldo_registrado = integracion.obtener_saldo_registrado(caja)
    if set(saldos_declarados) != set(saldo_registrado):
        raise ValidationError("Debés declarar el saldo de todas las monedas de la caja.")

    arqueo = ArqueoCaja.objects.create(cajero=cajero, **integracion.datos_de_caja(caja))
    for moneda, registrado in saldo_registrado.items():
        declarado = Decimal(saldos_declarados[moneda])
        diferencia, resultado = calcular_resultado(registrado, declarado)
        DetalleArqueo.objects.create(
            arqueo=arqueo,
            moneda=moneda,
            saldo_registrado=registrado,
            saldo_declarado=declarado,
            diferencia=diferencia,
            resultado=resultado,
        )

    integracion.bloquear_caja(caja)
    return arqueo
