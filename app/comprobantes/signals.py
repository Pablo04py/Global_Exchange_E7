"""Señales de la app comprobantes.

El envío se encola cuando una `FacturaElectronica` (SCRUM-56) queda `APROBADA`
por SIFEN. Hoy el estado se actualiza en `facturacion.services.emision.sincronizar_estado_sifen`,
que se llama al abrir el detalle de la transacción; cuando exista la consulta
periódica de SCRUM-22, el envío se dispara igual sin cambios en esta app.
"""

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from facturacion.models import FacturaElectronica

from .services import encolar_envio


@receiver(post_save, sender=FacturaElectronica, dispatch_uid='comprobantes_envio_factura_aprobada')
def encolar_envio_al_aprobar(sender, instance, **kwargs):
    """Encola el envío del KuDE cuando la factura queda `APROBADA`.

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
    transaction.on_commit(lambda: encolar_envio(instance), robust=True)
