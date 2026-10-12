from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from clientes.models import Cliente
from usuarios.decorators import requiere_rol

from . import caja_gateway
from .forms import CajaOperacionForm
from .models import Transaccion
from .services import CotizacionDesactualizada, simular_operacion
from .services_caja import operar_en_caja

CAMPOS_BUSQUEDA_CLIENTE = ['nombre_o_denominacion', 'documento']


def _huella(tipo, moneda, monto, forma_pago):
    return f"{tipo}|{moneda.pk}|{format(monto.normalize(), 'f')}|{forma_pago}"


@requiere_rol('Cajero')
def buscar_cliente_caja(request):
    """Paso 1: el cajero busca al cliente que está en el mostrador."""
    try:
        sesion = caja_gateway.obtener_sesion_abierta(request.user)
    except caja_gateway.SesionCajaNoAbierta as e:
        return render(request, 'operaciones/caja_buscar_cliente.html', {'sin_sesion': str(e)})

    q = request.GET.get('q', '').strip()
    clientes = []
    if q:
        filtro = Q()
        for campo in CAMPOS_BUSQUEDA_CLIENTE:
            filtro |= Q(**{f'{campo}__icontains': q})
        clientes = Cliente.objects.filter(filtro)[:20]

    return render(request, 'operaciones/caja_buscar_cliente.html',
                  {'q': q, 'clientes': clientes, 'sesion': sesion})



@requiere_rol('Cajero')
def operar_en_caja_view(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)

    try:
        sesion = caja_gateway.obtener_sesion_abierta(request.user)
    except caja_gateway.SesionCajaNoAbierta as e:
        messages.error(request, str(e))
        return redirect('caja_buscar_cliente')

    simulacion = None

    if request.method == 'POST':
        form = CajaOperacionForm(request.POST, cliente=cliente)
        if form.is_valid():
            tipo = form.cleaned_data['tipo_operacion']
            moneda = form.cleaned_data['moneda']
            monto = form.cleaned_data['monto']
            forma_pago = form.cleaned_data['forma_pago']
            accion = request.POST.get('accion')

            if accion == 'simular':
                try:
                    simulacion = simular_operacion(cliente=cliente, tipo_operacion=tipo,
                                                   moneda=moneda, monto=monto)
                    simulacion['huella'] = _huella(tipo, moneda, monto, forma_pago)
                    simulacion['moneda_origen'] = 'PYG' if tipo == Transaccion.Tipo.COMPRA else moneda.codigo
                    simulacion['moneda_destino'] = moneda.codigo if tipo == Transaccion.Tipo.COMPRA else 'PYG'
                    simulacion['en_efectivo'] = forma_pago == 'EFECTIVO'
                except ValidationError as e:
                    form.add_error(None, e.message)

            elif accion == 'confirmar':
                tasa_id = request.POST.get('tasa_id_simulada')
                if not tasa_id:
                    form.add_error(None, "Debe simular la operación antes de confirmarla.")
                elif request.POST.get('huella') != _huella(tipo, moneda, monto, forma_pago):
                    form.add_error(None, "Los datos cambiaron después de simular. Simule de nuevo.")
                else:
                    try:
                        tx = operar_en_caja(request.user, cliente, tipo, moneda,
                                            monto, tasa_id, forma_pago)
                        messages.success(request, "Operación confirmada y registrada en caja.")
                        return redirect('caja_ticket', transaccion_id=tx.id)
                    except CotizacionDesactualizada as e:
                        form.add_error(None, f"{e} (el cliente debe aceptar la nueva cotización)")
                    except caja_gateway.SesionCajaNoAbierta as e:
                        form.add_error(None, str(e))
                    except ValidationError as e:
                        form.add_error(None, e.message if hasattr(e, 'message') else str(e))
    else:
        form = CajaOperacionForm(cliente=cliente)

    return render(request, 'operaciones/caja_operar.html', {
        'form': form, 'cliente': cliente, 'simulacion': simulacion, 'sesion': sesion,
    })


@requiere_rol('Cajero')
def ticket_caja(request, transaccion_id):
    """Comprobante de una operación confirmada por el cajero actual."""
    tx = get_object_or_404(Transaccion, id=transaccion_id,
                           cajero=request.user, canal=Transaccion.Canal.CAJA)
    return render(request, 'operaciones/caja_ticket.html', {'transaccion': tx})


@requiere_rol('Cajero')
def historial_caja_dia(request):
    """Operaciones que el cajero actual confirmó hoy, con el saldo de su caja."""
    hoy = timezone.localdate()
    transacciones = (
        Transaccion.objects
        .filter(cajero=request.user, canal=Transaccion.Canal.CAJA, fecha__date=hoy)
        .select_related('cliente', 'moneda', 'medio_pago')
        .order_by('-fecha')
    )

    try:
        sesion = caja_gateway.obtener_sesion_abierta(request.user)
        saldos = caja_gateway.obtener_saldos(sesion)
    except caja_gateway.SesionCajaNoAbierta:
        sesion, saldos = None, {}

    return render(request, 'operaciones/caja_historial_dia.html', {
        'transacciones': transacciones,
        'total': transacciones.count(),
        'saldos': saldos,
        'sesion': sesion,
        'hoy': hoy,
    })