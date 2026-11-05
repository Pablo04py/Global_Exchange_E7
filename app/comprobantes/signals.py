"""Señales de la app comprobantes.

- Las facturas reales las envía Factura Segura al emitirlas, al correo del
  cliente que va en el Documento Electrónico (`dEmailRec`, ver
  `comprobantes.destinatarios`). El envío propio por el mailer se encola cuando
  una factura simulada queda `APROBADA`, o también las reales si se activa
  `COMPROBANTES_ENVIO_PROPIO_REALES` como respaldo.
- Con el modo simulación activo (ver `comprobantes.simulacion`), al pasar una
  `Transaccion` a `PAGADA` se genera su factura aprobada simulada, que a su vez
  dispara el envío.
"""

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from facturacion.models import FacturaElectronica
from operaciones.models import Transaccion

from .services import encolar_envio
from .simulacion import emitir_factura_simulada, es_factura_simulada, simulacion_activa


@receiver(post_save, sender=FacturaElectronica, dispatch_uid='comprobantes_envio_factura_aprobada')
def encolar_envio_al_aprobar(sender, instance, **kwargs):
    """Encola el envío propio cuando la factura queda `APROBADA`.

    Solo para facturas simuladas, o reales con `COMPROBANTES_ENVIO_PROPIO_REALES`.
    No usa `update_fields` porque `sincronizar_estado_sifen` guarda la factura
    completa. Los guardados repetidos no duplican el envío (ver `encolar_envio`).

    El encolado se ejecuta con `transaction.on_commit`, es decir, solo si la
    aprobación quedó guardada. Con `robust=True` un error se registra en el log
    sin afectar a quien guardó la factura (por ejemplo, la vista de detalle).

    Args:
        sender: Clase `FacturaElectronica`.
        instance: Factura guardada.
        **kwargs: Argumentos adicionales de la señal.
    """
    if instance.estado != FacturaElectronica.Estado.APROBADA or not instance.cdc:
        return
    # Las facturas reales ya las envía Factura Segura al receptor (dEmailRec): el envío
    # propio queda para las simuladas, salvo que se active como respaldo.
    if not es_factura_simulada(instance) and not getattr(settings, 'COMPROBANTES_ENVIO_PROPIO_REALES', False):
        return
    transaction.on_commit(lambda: encolar_envio(instance), robust=True)


@receiver(post_save, sender=Transaccion, dispatch_uid='comprobantes_factura_simulada_al_pagar')
def simular_factura_al_pagar(sender, instance, created, update_fields=None, **kwargs):
    """Genera la factura aprobada simulada cuando la transacción pasa a `PAGADA`.

    Solo actúa con el modo simulación activo y ante cambios de estado
    (`update_fields` con `estado`, como guarda `cambiar_estado_transaccion`):
    las transacciones creadas directamente como pagadas (datos de prueba) no
    generan facturas. Se ejecuta con `on_commit(..., robust=True)`: solo si el
    pago quedó guardado y sin revertirlo ante un error.

    Args:
        sender: Clase `Transaccion`.
        instance: Transacción guardada.
        created: Si el registro es nuevo.
        update_fields: Campos guardados, o `None` si se guardaron todos.
        **kwargs: Argumentos adicionales de la señal.
    """
    if created or not update_fields or 'estado' not in update_fields:
        return
    if instance.estado != Transaccion.Estado.PAGADA or not simulacion_activa():
        return
    transaccion_id = instance.pk
    transaction.on_commit(lambda: emitir_factura_simulada(transaccion_id), robust=True)
