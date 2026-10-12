from decimal import Decimal, ROUND_HALF_UP

import stripe

from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse

from operaciones.models import Transaccion

def configurar_stripe():
    """
    Configura Stripe con la clave secreta.
    """

    if not settings.STRIPE_SECRET_KEY:
        raise ValidationError(
            "Stripe no está configurado correctamente."
        )

    stripe.api_key = settings.STRIPE_SECRET_KEY


def crear_payment_intent_tarjeta_guardada(
    transaccion
):
    """
    Crea un PaymentIntent para cobrar una transacción
    usando una tarjeta previamente registrada en Stripe.

    El PaymentIntent se crea sin confirmar, ya que el
    navegador debe solicitar nuevamente el CVC.
    """

    configurar_stripe()

    if (
        transaccion.estado
        != Transaccion.Estado.PENDIENTE
    ):
        raise ValidationError(
            "Solo se pueden pagar transacciones pendientes."
        )

    if transaccion.tipo != Transaccion.Tipo.COMPRA:
        raise ValidationError(
            "Stripe solo está disponible "
            "para operaciones de compra."
        )

    medio = transaccion.medio_pago

    if medio.tipo != 'TARJETA':
        raise ValidationError(
            "El medio seleccionado no es una tarjeta."
        )

    if not medio.stripe_payment_method_id:
        raise ValidationError(
            "La tarjeta seleccionada no está "
            "registrada en Stripe."
        )

    cliente = transaccion.cliente

    if not cliente.stripe_customer_id:
        raise ValidationError(
            "El cliente no está asociado a Stripe."
        )

    # Verificar directamente en Stripe que el
    # PaymentMethod pertenece al Customer correcto.
    payment_method = stripe.PaymentMethod.retrieve(
        medio.stripe_payment_method_id
    )

    if (
        payment_method.customer
        != cliente.stripe_customer_id
    ):
        raise ValidationError(
            "La tarjeta no pertenece "
            "al cliente seleccionado."
        )

    monto = Decimal(
        transaccion.monto_pagado
    ).quantize(
        Decimal('1'),
        rounding=ROUND_HALF_UP
    )

    monto_stripe = int(monto)

    if monto_stripe <= 0:
        raise ValidationError(
            "El monto del pago no es válido."
        )

    payment_intent = stripe.PaymentIntent.create(
        amount=monto_stripe,
        currency=settings.STRIPE_CURRENCY,

        customer=cliente.stripe_customer_id,

        payment_method=(
            medio.stripe_payment_method_id
        ),

        payment_method_options={
            'card': {
                'require_cvc_recollection': True
            }
        },

        metadata={
            'transaccion_id': str(
                transaccion.id
            ),
            'cliente_id': str(
                cliente.id
            ),
            'medio_pago_id': str(
                medio.id
            ),
        },

        idempotency_key=(
            f"global-exchange-transaccion-{transaccion.id}"
        ),
    )

    return payment_intent