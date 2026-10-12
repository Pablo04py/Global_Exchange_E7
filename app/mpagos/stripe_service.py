import stripe 

from django.conf import settings
from django.core.exceptions import ValidationError

def configurar_stripe():
    """
    Configura el SDK de Stripe con la clave secreta del proyecto.
    """

    if not settings.STRIPE_SECRET_KEY:
        raise ValidationError(
            "Stripe no está configurado correctamente."
        )

    stripe.api_key = settings.STRIPE_SECRET_KEY


def obtener_o_crear_stripe_customer(cliente):
    """
    Obtiene el Customer de Stripe asociado al cliente.

    Si el cliente todavía no posee uno, crea un Customer
    en Stripe y guarda su identificador localmente.
    """

    configurar_stripe()

    if cliente.stripe_customer_id:
        return cliente.stripe_customer_id

    customer = stripe.Customer.create(
        name=cliente.nombre_o_denominacion,
        metadata={
            'cliente_id': str(cliente.id),
            'documento': cliente.documento,
        }
    )

    cliente.stripe_customer_id = customer.id

    cliente.save(
        update_fields=['stripe_customer_id']
    )

    return customer.id


def crear_setup_intent_tarjeta(cliente):
    """
    Crea un SetupIntent para registrar una tarjeta
    que podrá reutilizarse en operaciones futuras.
    """

    configurar_stripe()

    customer_id = obtener_o_crear_stripe_customer(
        cliente
    )

    setup_intent = stripe.SetupIntent.create(
        customer=customer_id,

        allowed_payment_method_types=[
            'card'
        ],

        usage='on_session',

        metadata={
            'cliente_id': str(cliente.id),
        }
    )

    return setup_intent

def obtener_tarjeta_confirmada(
    cliente,
    setup_intent_id
):
    """
    Recupera y valida una tarjeta confirmada mediante
    un SetupIntent de Stripe.
    """

    configurar_stripe()

    setup_intent = stripe.SetupIntent.retrieve(
        setup_intent_id
    )

    # El SetupIntent debe pertenecer al Customer
    # Stripe del cliente activo.
    if (
        setup_intent.customer
        != cliente.stripe_customer_id
    ):
        raise ValidationError(
            "La tarjeta no pertenece al cliente activo."
        )

    metadata = (
        setup_intent.metadata.to_dict()
        if setup_intent.metadata
        else {}
    )

    cliente_metadata = metadata.get(
        'cliente_id'
    )

    if str(cliente_metadata) != str(cliente.id):
        raise ValidationError(
            "El registro de tarjeta no corresponde "
            "al cliente activo."
        )

    # Solo aceptamos una tarjeta cuya configuración
    # terminó correctamente.
    if setup_intent.status != 'succeeded':
        raise ValidationError("La tarjeta todavía no fue confirmada.")

    if not setup_intent.payment_method:
        raise ValidationError(
            "Stripe no devolvió un método de pago."
        )

    payment_method = stripe.PaymentMethod.retrieve(
        setup_intent.payment_method
    )

    if payment_method.type != 'card':
        raise ValidationError(
            "El método registrado no corresponde "
            "a una tarjeta."
        )

    return payment_method