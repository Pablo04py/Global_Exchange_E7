"""Modo simulación de facturas para desarrollo y demostración (SCRUM-23).

Con `COMPROBANTES_SIMULAR_FACTURA=True`, cada transacción que pasa a `PAGADA`
genera una `FacturaElectronica` ya `APROBADA`, sin llamar a Factura Segura ni
consumir numeración fiscal del ambiente TEST. Así se puede probar el envío por
email sin depender de SIFEN.

Las facturas simuladas usan una serie propia (`9000001`, `9000002`, ...) y un
CDC que empieza con `SIMULADO`; no tienen validez fiscal. El modo no actúa si
la emisión real de SCRUM-56 (`FACTURACION_EMISION_AUTOMATICA`) está encendida,
para que una transacción nunca tenga dos facturas.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from facturacion.models import ConfiguracionFacturacion, FacturaElectronica
from operaciones.models import Transaccion

logger = logging.getLogger(__name__)

PREFIJO_CDC_SIMULADO = 'SIMULADO'
PRIMER_NUMERO_SIMULADO = 9000001
LARGO_CDC = 44


def simulacion_activa():
    """Indica si corresponde simular las facturas al confirmar un pago.

    Returns:
        bool: `True` si `COMPROBANTES_SIMULAR_FACTURA` está encendido y la
        emisión real (`FACTURACION_EMISION_AUTOMATICA`) está apagada.
    """
    return (getattr(settings, 'COMPROBANTES_SIMULAR_FACTURA', False)
            and not getattr(settings, 'FACTURACION_EMISION_AUTOMATICA', False))


def es_factura_simulada(factura):
    """Indica si la factura fue generada por el modo simulación.

    Args:
        factura: Factura electrónica.

    Returns:
        bool: `True` si su CDC empieza con `SIMULADO`.
    """
    return bool(factura.cdc) and factura.cdc.startswith(PREFIJO_CDC_SIMULADO)


def _siguiente_numero_simulado(configuracion):
    """Siguiente número de la serie simulada para la configuración.

    Debe llamarse con la configuración bloqueada (`select_for_update`).

    Args:
        configuracion: Configuración fiscal activa.

    Returns:
        str: Número de 7 dígitos (`9000001` o el siguiente al último usado).
    """
    ultimo = FacturaElectronica.objects.filter(
        configuracion=configuracion, cdc__startswith=PREFIJO_CDC_SIMULADO,
    ).aggregate(maximo=Max('numero_documento'))['maximo']
    siguiente = max(int(ultimo) + 1, PRIMER_NUMERO_SIMULADO) if ultimo else PRIMER_NUMERO_SIMULADO
    return f"{siguiente:07d}"


def emitir_factura_simulada(transaccion_id):
    """Crea la factura `APROBADA` simulada de una transacción pagada.

    No toca `ConfiguracionFacturacion.siguiente_numero_documento` (la
    numeración fiscal real queda intacta). Al guardarse la factura aprobada,
    la señal de `comprobantes` encola su envío por email.

    Args:
        transaccion_id: Id de la transacción que acaba de pasar a `PAGADA`.

    Returns:
        FacturaElectronica | None: La factura simulada, o `None` si el modo
        está inactivo, la transacción no está pagada, ya tiene factura o no
        hay una configuración fiscal activa.
    """
    if not simulacion_activa():
        return None

    with transaction.atomic():
        configuracion = ConfiguracionFacturacion.objects.select_for_update().filter(activa=True).first()
        if configuracion is None:
            logger.warning("Factura simulada no generada para %s: no hay configuración de facturación activa.",
                           transaccion_id)
            return None

        tx = Transaccion.objects.select_for_update().get(pk=transaccion_id)
        if tx.estado != Transaccion.Estado.PAGADA or FacturaElectronica.objects.filter(transaccion=tx).exists():
            return None

        factura = FacturaElectronica.objects.create(
            transaccion=tx,
            configuracion=configuracion,
            numero_documento=_siguiente_numero_simulado(configuracion),
            cdc=(PREFIJO_CDC_SIMULADO + tx.id.hex).ljust(LARGO_CDC, '0')[:LARGO_CDC],
            estado=FacturaElectronica.Estado.APROBADA,
            fecha_aprobacion=timezone.now(),
            descripcion_respuesta='SIMULACIÓN LOCAL (SCRUM-23): no emitida en SIFEN',
            json_resumido={'simulada': True},
        )
        tx.facturada = True
        tx.save(update_fields=['facturada'])

    logger.info("Factura simulada %s generada para la transacción %s.", factura.numero_documento, tx.id)
    return factura
