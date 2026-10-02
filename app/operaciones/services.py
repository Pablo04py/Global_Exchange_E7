from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    LogTransaccion,
    TasaDeCambio,
    Transaccion,
    ConfiguracionComision
)

CUATRO_DECIMALES = Decimal('0.0001')

class CotizacionDesactualizada(Exception):
    pass

def obtener_tasa_vigente(moneda):
    """
    Obtiene la tasa más reciente de una moneda.
    """

    tasa = (
        TasaDeCambio.objects
        .filter(moneda=moneda)
        .order_by('-fecha_vigencia')
        .first()
    )

    if not tasa:
        raise ValidationError(
            "La moneda seleccionada no posee una tasa de cambio vigente."
        )

    return tasa

def obtener_porcentaje_comision(cliente):
    """
    Obtiene la comisión configurada para la categoría del cliente.
    """

    configuracion = (
        ConfiguracionComision.objects
        .filter(categoria=cliente.categoria)
        .first()
    )

    if not configuracion:
        raise ValidationError(
            f"No existe una comisión configurada para "
            f"{cliente.get_categoria_display()}."
        )

    return configuracion.porcentaje

def calcular_operacion(tipo_operacion, monto, tasa, porcentaje_comision):
    """
    Calcula una compra o venta de divisas.
    """

    if monto <= 0:
        raise ValidationError(
            "El monto debe ser mayor a cero."
        )

    factor_comision = porcentaje_comision / Decimal('100')

    if tipo_operacion == Transaccion.Tipo.COMPRA:

        # El cliente compra divisa.
        # Global Exchange vende la divisa.
        tasa_aplicada = tasa.calcular_precio_venta()

        monto_bruto = monto / tasa_aplicada

        monto_comision = (
            monto_bruto * factor_comision
        )

        monto_destino = (
            monto_bruto - monto_comision
        )

        moneda_comision = tasa.moneda.codigo

    elif tipo_operacion == Transaccion.Tipo.VENTA:

        # El cliente vende divisa.
        # Global Exchange compra la divisa.
        tasa_aplicada = tasa.calcular_precio_compra()

        monto_bruto = monto * tasa_aplicada

        monto_comision = (
            monto_bruto * factor_comision
        )

        monto_destino = (
            monto_bruto - monto_comision
        )

        moneda_comision = 'PYG'

    else:
        raise ValidationError(
            "Tipo de operación inválido."
        )

    return {
        'monto_origen': monto.quantize(
            CUATRO_DECIMALES,
            rounding=ROUND_HALF_UP
        ),

        'monto_bruto': monto_bruto.quantize(
            CUATRO_DECIMALES,
            rounding=ROUND_HALF_UP
        ),

        'monto_destino': monto_destino.quantize(
            CUATRO_DECIMALES,
            rounding=ROUND_HALF_UP
        ),

        'tasa_aplicada': tasa_aplicada.quantize(
            CUATRO_DECIMALES,
            rounding=ROUND_HALF_UP
        ),

        'porcentaje_comision': porcentaje_comision,

        'monto_comision': monto_comision.quantize(
            CUATRO_DECIMALES,
            rounding=ROUND_HALF_UP
        ),

        'moneda_comision': moneda_comision,
    }

def simular_operacion(
    cliente,
    tipo_operacion,
    moneda,
    monto
):
    """
    Realiza una simulación sin guardar una transacción.
    """

    tasa = obtener_tasa_vigente(moneda)

    porcentaje = obtener_porcentaje_comision(
        cliente
    )

    resultado = calcular_operacion(
        tipo_operacion,
        monto,
        tasa,
        porcentaje
    )

    resultado['tasa_id'] = str(tasa.id)

    return resultado

@transaction.atomic
def crear_transaccion(
    usuario,
    cliente,
    tipo_operacion,
    moneda,
    monto,
    medio_pago,
    tasa_id_simulada
):
    """
    Crea una transacción PENDIENTE utilizando la tasa
    mostrada durante la simulación.
    """

    tasa_actual = obtener_tasa_vigente(moneda)

    # El usuario tiene que confirmar exactamente la tasa
    # que se le mostró en la simulación.
    if str(tasa_actual.id) != str(tasa_id_simulada):
        raise CotizacionDesactualizada(
            "La cotización cambió. "
            "Debe volver a simular la operación."
        )

    if not medio_pago.activo:
        raise ValidationError(
            "El medio de pago seleccionado no está activo."
        )

    if medio_pago.cliente_id != cliente.id:
        raise ValidationError(
            "El medio de pago no pertenece al cliente seleccionado."
        )

    porcentaje = obtener_porcentaje_comision(
        cliente
    )

    resultado = calcular_operacion(
        tipo_operacion,
        monto,
        tasa_actual,
        porcentaje
    )

    transaccion = Transaccion.objects.create(
        usuario=usuario,
        cliente=cliente,
        moneda=moneda,
        tipo=tipo_operacion,

        monto_pagado = resultado['monto_origen'],
        monto_recibido = resultado['monto_destino'],

        tasa_referencia=tasa_actual,
        tasa_aplicada=resultado['tasa_aplicada'],

        categoria_cliente_aplicada=cliente.categoria,

        porcentaje_comision=resultado[
            'porcentaje_comision'
        ],

        monto_comision=resultado[
            'monto_comision'
        ],

        moneda_comision=resultado[
            'moneda_comision'
        ],

        medio_pago=medio_pago,

        estado=Transaccion.Estado.PENDIENTE,
    )

    return transaccion

@transaction.atomic
def cambiar_estado_transaccion(transaccion, nuevo_estado, usuario, motivo=""):
    """
    Cambia el estado de una transacción y guarda el log de auditoría inmutable (RNF15).
    En el Sprint 3 solo se permite la transición PENDIENTE -> CANCELADA.
    """
    estado_anterior = transaccion.estado

    # Reglas de transición para el Sprint 3
    TRANSICIONES_PERMITIDAS = {
        Transaccion.Estado.PENDIENTE: [Transaccion.Estado.CANCELADA],
        Transaccion.Estado.CANCELADA: [],   # Estado terminal: no se puede reabrir
        Transaccion.Estado.CONFIRMADA: [],  # Estado terminal
    }

    if nuevo_estado not in TRANSICIONES_PERMITIDAS.get(estado_anterior, []):
        raise ValidationError(
            f"Transición no permitida: no se puede pasar de '{estado_anterior}' a '{nuevo_estado}'."
        )

    # 1. Actualizar estado
    transaccion.estado = nuevo_estado
    transaccion.save(update_fields=['estado'])

    # 2. Registrar log de auditoría inmutable
    LogTransaccion.objects.create(
        transaccion=transaccion,
        estado_anterior=estado_anterior,
        estado_nuevo=nuevo_estado,
        usuario=usuario,
        motivo=motivo
    )

    return transaccion
