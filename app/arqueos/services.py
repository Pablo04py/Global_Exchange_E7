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
    """Cierra el turno abierto del cajero, registra el arqueo y bloquea la caja.

    Todo ocurre en una única transacción de base de datos: si algo falla, no
    queda ni el arqueo ni el cierre a medias. La fila del turno se bloquea
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
    turno = integracion.obtener_turno_abierto(cajero, bloquear_fila=True)
    if turno is None:
        raise ValidationError("No tenés una caja abierta asignada para cerrar.")

    saldo_registrado = integracion.obtener_saldo_registrado(turno)
    if set(saldos_declarados) != set(saldo_registrado):
        raise ValidationError("Debés declarar el saldo de todas las monedas de la caja.")

    arqueo = ArqueoCaja.objects.create(cajero=cajero, **integracion.datos_de_caja(turno))
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

    integracion.cerrar_turno_y_bloquear_caja(turno)
    return arqueo


def cajas_bloqueadas_con_ultimo_cierre():
    """Lista las cajas bloqueadas por un cierre junto con su último arqueo.

    Solo incluye las cajas bloqueadas que tienen al menos un arqueo, para no
    listar cajas desactivadas por otros motivos.

    Returns:
        list[dict]: Cada elemento tiene `caja` y `ultimo_arqueo`, ordenados
        del cierre más reciente al más antiguo.
    """
    resultado = []
    for caja in integracion.cajas_bloqueadas():
        ultimo = (
            ArqueoCaja.objects.filter(caja_id=str(caja.pk))
            .select_related('cajero').prefetch_related('detalles').first()
        )
        if ultimo is not None:
            resultado.append({'caja': caja, 'ultimo_arqueo': ultimo})
    return sorted(resultado, key=lambda item: item['ultimo_arqueo'].fecha_cierre, reverse=True)


@transaction.atomic
def habilitar_caja_bloqueada(caja_id):
    """Habilita nuevamente una caja bloqueada por un cierre.

    Args:
        caja_id: Identificador de la caja.

    Returns:
        Model: La caja habilitada.

    Raises:
        ValidationError: Si la caja no existe, no está bloqueada o no tiene un
            cierre registrado.
        integracion.ModuloCajaNoDisponible: Si el módulo de caja no está disponible.
    """
    caja = integracion.cajas_bloqueadas().select_for_update().filter(pk=caja_id).first()
    if caja is None or not ArqueoCaja.objects.filter(caja_id=str(caja.pk)).exists():
        raise ValidationError("La caja no está bloqueada por un cierre o ya fue habilitada.")
    integracion.habilitar_caja(caja)
    return caja
