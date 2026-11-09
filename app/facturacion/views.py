
import logging

from django.contrib import messages
from django.core.paginator import Paginator
from clientes.models import UsuarioCliente
from main.views import get_menu_sections, resolve_user_role, resolve_user_roles

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .models import FacturaElectronica
from .services.factura_segura import (
    FacturaSeguraService,
    FacturaSeguraError,
)

logger = logging.getLogger(__name__)

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
        transaccion__usuario=request.user,    
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

    except FacturaSeguraError:
        logger.exception('Error descargando KuDE de factura %s', factura.pk)
        return HttpResponse('No se pudo descargar el PDF.', status=502)

    if hasattr(contenido, 'content'):
        contenido = contenido.content
    if not isinstance(contenido, (bytes, bytearray)) or not contenido.startswith(b'%PDF'):
        logger.error('Respuesta no PDF del proveedor para factura %s', factura.pk)
        return HttpResponse('El proveedor no devolvió un PDF válido.', status=502)

    response = HttpResponse(
        bytes(contenido),
        content_type='application/pdf',
    )

    response[
        'Content-Disposition'
    ] = (
        f'attachment; '
        f'filename="factura_{factura.numero_documento}.pdf"'
    )

    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
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

    except FacturaSeguraError:
        logger.exception('Error descargando XML de factura %s', factura.pk)
        return HttpResponse('No se pudo descargar el XML.', status=502)

    if hasattr(contenido, 'content'):
        contenido = contenido.content
    if not isinstance(contenido, (bytes, bytearray)) or not contenido.strip():
        logger.error('Respuesta XML vacía o inválida para factura %s', factura.pk)
        return HttpResponse('El proveedor no devolvió un XML válido.', status=502)

    response = HttpResponse(
        bytes(contenido),
        content_type='application/xml',
    )

    response[
        'Content-Disposition'
    ] = (
        f'attachment; '
        f'filename="factura_{factura.numero_documento}.xml"'
    )

    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response

def _contexto_navegacion(request):
    """Reproduce el contexto que necesita layouts/base.html en páginas autenticadas.

    No concede acceso por rol global: los clientes visibles se filtran por
    las asociaciones reales UsuarioCliente del usuario autenticado.
    """
    asociaciones = (
        UsuarioCliente.objects.select_related('cliente')
        .filter(usuario=request.user)
        .order_by('cliente__nombre_o_denominacion')
    )
    asociados = [
        {
            'id': str(asociacion.cliente_id),
            'name': asociacion.cliente.nombre_o_denominacion,
            'category': asociacion.cliente.get_categoria_display(),
            'role': asociacion.rol_cliente,
            'role_label': asociacion.get_rol_cliente_display(),
        }
        for asociacion in asociaciones
    ]

    id_activo = str(request.session.get('ge_active_client') or '')
    cliente_activo = next((c for c in asociados if c['id'] == id_activo), None)
    if cliente_activo is None and asociados:
        cliente_activo = asociados[0]
        request.session['ge_active_client'] = cliente_activo['id']

    rol = resolve_user_role(request)
    rol_label = (
        rol if rol != 'Sin Rol' else (
            f"{cliente_activo['role_label']} de Cliente"
            if cliente_activo else 'Cliente sin registrar'
        )
    )
    return {
        'user_role': rol,
        'user_role_label': rol_label,
        'associated_clients': asociados,
        'active_client': cliente_activo,
        'menu_sections': get_menu_sections(
            rol,
            cliente_activo,
            is_authenticated=True,
            roles=resolve_user_roles(request),
        ),
    }

@login_required
@require_GET
def lista_facturas(request):
    """Muestra exclusivamente facturas de transacciones realizadas por el usuario.

    No consulta Factura Segura: muestra el último estado guardado localmente.
    No filtra por ge_active_client porque es un historial PERSONAL que puede
    incluir operaciones de varios clientes para los cuales operó el usuario.
    """
    facturas = (
        FacturaElectronica.objects
        .filter(transaccion__usuario=request.user)
        .select_related('transaccion__cliente', 'configuracion')
        .order_by('-fecha_creacion')
    )
    estado = request.GET.get('estado', '')
    estados_validos = {valor for valor, _ in FacturaElectronica.Estado.choices}
    if estado in estados_validos:
        facturas = facturas.filter(estado=estado)
    else:
        estado = ''

    pagina = Paginator(facturas, 10).get_page(request.GET.get('page'))
    contexto = _contexto_navegacion(request)
    contexto.update({
        'page_obj': pagina,
        'estado_filtro': estado,
        'estados': FacturaElectronica.Estado.choices,
        'total_facturas': pagina.paginator.count,
    })
    return render(request, 'facturacion/lista_facturas.html', contexto)