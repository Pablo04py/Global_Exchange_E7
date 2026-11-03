"""Señales de la app comprobantes.

El envío se dispara al guardar una `Transaccion` cuyo estado cambió a `PAGADA`.
Todas las vías de pago (Stripe, SIPAP, efectivo y caja) pasan por
`operaciones.services.cambiar_estado_transaccion`, que guarda con
`update_fields=['estado']`, así que no hace falta modificar la app operaciones.
"""

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from operaciones.models import Transaccion

from .services import encolar_envio


@receiver(post_save, sender=Transaccion, dispatch_uid='comprobantes_envio_al_pagar')
def encolar_envio_al_pagar(sender, instance, created, update_fields=None, **kwargs):
    """Programa el envío del comprobante cuando la transacción pasa a `PAGADA`.

    Solo reacciona a cambios de estado (`update_fields` con `estado`): las
    transacciones creadas directamente como pagadas (por ejemplo, los datos de
    prueba de `generar_transacciones_prueba`) no generan correos.

    El envío se ejecuta con `transaction.on_commit`, es decir, solo si el pago
    quedó guardado en la base de datos. Con `robust=True` un error en el envío
    se registra en el log pero no afecta la confirmación del pago.

    Args:
        sender: Clase `Transaccion`.
        instance: Transacción guardada.
        created: Si el registro es nuevo.
        update_fields: Campos guardados, o `None` si se guardaron todos.
        **kwargs: Argumentos adicionales de la señal.
    """
    if created or not update_fields or 'estado' not in update_fields:
        return
    if instance.estado != Transaccion.Estado.PAGADA:
        return
    transaction.on_commit(lambda: encolar_envio(instance), robust=True)
