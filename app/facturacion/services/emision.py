from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from operaciones.models import Transaccion

from facturacion.models import (
    ConfiguracionFacturacion,
    FacturaElectronica,
)

from .factura_builder import construir_json_resumido

from .factura_segura import (
    FacturaSeguraService,
    FacturaSeguraError,
)


class ErrorEmisionFactura(Exception):
    pass


def emitir_factura(transaccion):
    """
    Emite la factura electrónica de una transacción PAGADA.

    Es idempotente:
    si la transacción ya posee una factura generada,
    no vuelve a llamar generar_de.
    """

    if transaccion.estado != Transaccion.Estado.PAGADA:
        raise ValidationError(
            'Solo se pueden facturar transacciones PAGADAS.'
        )

    # Evitar facturación duplicada.
    factura_existente = (
        FacturaElectronica.objects
        .filter(transaccion=transaccion)
        .first()
    )

    if factura_existente and factura_existente.cdc:
        return factura_existente

    configuracion = (
        ConfiguracionFacturacion.objects
        .filter(activa=True)
        .first()
    )

    if not configuracion:
        raise ErrorEmisionFactura(
            'No existe una configuración de facturación activa.'
        )

    numero_documento = (
        configuracion.siguiente_numero_documento
    )

    de_resumido = construir_json_resumido(
        transaccion=transaccion,
        configuracion=configuracion,
        numero_documento=numero_documento,
    )

    # --------------------------------------------------
    # 1. CALCULAR DE
    # --------------------------------------------------

    try:
        respuesta_calculo = (
            FacturaSeguraService.calcular_de(
                de_resumido
            )
        )

    except FacturaSeguraError as exc:
        raise ErrorEmisionFactura(
            f'Error calculando DE: {exc}'
        ) from exc

    de_calculado = (
        respuesta_calculo['results'][0]['DE']
    )

    numero_texto = de_resumido['dNumDoc']

    # Guardamos la factura antes de generar.
    factura, _ = (
        FacturaElectronica.objects
        .update_or_create(
            transaccion=transaccion,
            defaults={
                'configuracion': configuracion,
                'numero_documento': numero_texto,
                'estado': (
                    FacturaElectronica.Estado.CALCULADA
                ),
                'operation_id': (
                    respuesta_calculo[
                        'operation_info'
                    ]['id']
                ),
                'codigo_respuesta': (
                    respuesta_calculo['code']
                ),
                'descripcion_respuesta': (
                    respuesta_calculo[
                        'description'
                    ]
                ),
                'json_resumido': de_resumido,
                'json_calculado': de_calculado,
            }
        )
    )

    # --------------------------------------------------
    # 2. GENERAR DE
    # --------------------------------------------------

    try:
        respuesta_generacion = (
            FacturaSeguraService.generar_de(
                de_calculado
            )
        )

    except FacturaSeguraError as exc:

        factura.estado = (
            FacturaElectronica.Estado.ERROR
        )

        factura.descripcion_respuesta = str(exc)

        factura.save(
            update_fields=[
                'estado',
                'descripcion_respuesta',
                'fecha_actualizacion',
            ]
        )

        raise ErrorEmisionFactura(
            f'Error generando DE: {exc}'
        ) from exc

    cdc = (
        respuesta_generacion[
            'results'
        ][0]['CDC']
    )

    # --------------------------------------------------
    # 3. GUARDAR GENERACIÓN
    # --------------------------------------------------

    factura.cdc = cdc

    factura.estado = (
        FacturaElectronica.Estado.EMITIDA
    )

    factura.operation_id = (
        respuesta_generacion[
            'operation_info'
        ]['id']
    )

    factura.codigo_respuesta = (
        respuesta_generacion['code']
    )

    factura.descripcion_respuesta = (
        respuesta_generacion['description']
    )

    factura.json_respuesta_generacion = (
        respuesta_generacion
    )

    factura.save()

    # --------------------------------------------------
    # 4. MARCAR TRANSACCIÓN FACTURADA
    # --------------------------------------------------

    transaccion.facturada = True

    transaccion.save(
        update_fields=['facturada']
    )

    # --------------------------------------------------
    # 5. AVANZAR NUMERACIÓN
    # --------------------------------------------------

    configuracion.siguiente_numero_documento = (
        numero_documento + 1
    )

    configuracion.save(
        update_fields=[
            'siguiente_numero_documento'
        ]
    )

    return factura

def sincronizar_estado_sifen(factura):
    """
    Consulta Factura Segura y actualiza
    el estado local de la factura.
    """

    if not factura.cdc:
        raise ValidationError(
            'La factura todavía no posee CDC.'
        )

    respuesta = (
        FacturaSeguraService.get_estado_sifen(
            cdc=factura.cdc,
            ruc_emisor=(
                factura.configuracion.ruc_emisor
            ),
        )
    )

    if not respuesta.get('results'):
        return factura

    resultado = respuesta['results'][0]

    estado_sifen = (
        resultado.get('estado_sifen') or ''
    )

    descripcion = (
        resultado.get('desc_sifen') or ''
    )

    error = (
        resultado.get('error_sifen') or ''
    )

    if estado_sifen in (
        'Aprobado',
        'Aprobado con observación',
    ):

        factura.estado = (
            FacturaElectronica.Estado.APROBADA
        )

        if not factura.fecha_aprobacion:
            factura.fecha_aprobacion = (
                timezone.now()
            )

    elif estado_sifen == 'Rechazado':

        factura.estado = (
            FacturaElectronica.Estado.RECHAZADA
        )

    elif estado_sifen in (
        'ERROR_SIFEN',
        'ERROR_ENVIO_LOTE',
        'REINTENTAR_LOTE',
        'ERROR_CONSULTA_LOTE',
        'Reingresado',
    ):

        factura.estado = (
            FacturaElectronica.Estado.ERROR
        )

    else:

        # SOL.APROBACION / ENVIADO_A_SIFEN
        factura.estado = (
            FacturaElectronica.Estado.EMITIDA
        )

    mensaje = descripcion

    if error:
        mensaje = (
            f'{descripcion} | {error}'
            if descripcion
            else error
        )

    factura.descripcion_respuesta = mensaje

    factura.save()

    return factura