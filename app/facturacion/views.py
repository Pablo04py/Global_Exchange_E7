from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from .models import FacturaElectronica
from .services.factura_segura import (
    FacturaSeguraService,
    FacturaSeguraError,
)


def _obtener_factura_usuario(request, factura_id):
    """
    Obtiene una factura perteneciente a un cliente
    asociado al usuario autenticado.
    """
    return get_object_or_404(
        FacturaElectronica.objects.select_related(
            'transaccion',
            'transaccion__cliente',
            'configuracion',
        ),
        id=factura_id,
        transaccion__cliente__usuarios_asociados__usuario=request.user,
    )


@login_required
@require_GET
def descargar_kude(request, factura_id):
    factura = _obtener_factura_usuario(
        request,
        factura_id,
    )

    if (
        factura.estado
        != FacturaElectronica.Estado.APROBADA
        or not factura.cdc
    ):
        return HttpResponse(
            'La factura todavía no está aprobada por SIFEN.',
            status=409,
        )

    try:
        contenido = FacturaSeguraService.descargar_kude(
            ruc_emisor=factura.configuracion.ruc_emisor,
            cdc=factura.cdc,
        )

    except FacturaSeguraError as exc:
        return HttpResponse(
            f'No se pudo descargar el KuDE: {exc}',
            status=502,
        )

    response = HttpResponse(
        contenido,
        content_type='application/pdf',
    )

    response[
        'Content-Disposition'
    ] = (
        f'attachment; '
        f'filename="factura_{factura.numero_documento}.pdf"'
    )

    return response


@login_required
@require_GET
def descargar_xml(request, factura_id):
    factura = _obtener_factura_usuario(
        request,
        factura_id,
    )

    if (
        factura.estado
        != FacturaElectronica.Estado.APROBADA
        or not factura.cdc
    ):
        return HttpResponse(
            'La factura todavía no está aprobada por SIFEN.',
            status=409,
        )

    try:
        contenido = FacturaSeguraService.descargar_xml(
            ruc_emisor=factura.configuracion.ruc_emisor,
            cdc=factura.cdc,
        )

    except FacturaSeguraError as exc:
        return HttpResponse(
            f'No se pudo descargar el XML: {exc}',
            status=502,
        )

    response = HttpResponse(
        contenido,
        content_type='application/xml',
    )

    response[
        'Content-Disposition'
    ] = (
        f'attachment; '
        f'filename="factura_{factura.numero_documento}.xml"'
    )

    return response