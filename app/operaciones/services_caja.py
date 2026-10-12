from django.db import transaction
from django.core.exceptions import ValidationError
from mpagos.models import MedioPago

from . import caja_gateway
from .models import Transaccion
from .services import cambiar_estado_transaccion, crear_transaccion

TIPO_EFECTIVO = 'EFECTIVO'

NOMBRES_MEDIO_CAJA = {
    'EFECTIVO': 'Efectivo en caja',
    'TARJETA': 'Tarjeta (POS de caja)',
    'SIPAP': 'Transferencia (caja)',
}



def obtener_medio_pago_caja(cliente, cajero, tipo):
    """Medio de pago genérico de caja para el cliente, creándolo si no existe."""
    if tipo not in NOMBRES_MEDIO_CAJA:
        raise ValidationError("Forma de pago inválida.")
    etiqueta = NOMBRES_MEDIO_CAJA[tipo]
    medio = MedioPago.objects.filter(
        cliente=cliente, tipo=tipo, activo=True, numero_enmascarado=etiqueta
    ).first()
    if medio is None:
        medio = MedioPago.objects.create(
            usuario=cajero, cliente=cliente, tipo=tipo,
            nombre_titular=cliente.nombre_o_denominacion[:150],
            numero_enmascarado=etiqueta,
        )
    return medio


@transaction.atomic
def operar_en_caja(cajero, cliente, tipo_operacion, moneda, monto,
                   tasa_id_simulada, forma_pago='EFECTIVO'):
    """Crea y confirma una operación presencial en un solo paso atómico."""
    sesion = caja_gateway.obtener_sesion_abierta(cajero, bloquear=True)
    medio_pago = obtener_medio_pago_caja(cliente, cajero, forma_pago)

    tx = crear_transaccion(
        usuario=cajero, cliente=cliente, tipo_operacion=tipo_operacion,
        moneda=moneda, monto=monto, medio_pago=medio_pago,
        tasa_id_simulada=tasa_id_simulada, canal=Transaccion.Canal.CAJA,
    )
    tx.cajero = cajero
    tx.save(update_fields=['cajero'])

    cambiar_estado_transaccion(
        tx, Transaccion.Estado.PAGADA, cajero,
        motivo=f"Operación presencial en {sesion.caja} ({medio_pago.get_tipo_display()})",
    )
    caja_gateway.registrar_movimiento(sesion, tx)
    return tx