from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.urls import reverse

from arqueos import integracion
from arqueos.forms import CierreCajaForm
from arqueos.models import ArqueoCaja
from arqueos.services import registrar_cierre
from main.views import get_menu_sections, resolve_user_role, resolve_user_roles

from .models import SesionCaja, EstadoSesionCaja
from .forms import AsignarCajeroForm, AperturaCajaForm
from .services import (
    asignar_cajero, apertura_caja, nombre_usuario,
)

PERMISO_ADMIN_CAJAS = 'caja.add_sesioncaja'


@login_required
@permission_required(PERMISO_ADMIN_CAJAS, raise_exception=True)
def asignar_cajero_view(request):
    """
    SCRUM-36: Permite a un administrador asignar una caja disponible a un cajero.
    """
    if request.method == 'POST':
        form = AsignarCajeroForm(request.POST)
        if form.is_valid():
            try:
                sesion = asignar_cajero(
                    form.cleaned_data['caja'],
                    form.cleaned_data['cajero'],
                    request.user,
                )
            except ValidationError as e:
                form.add_error(None, e.messages)
            else:
                messages.success(
                    request,
                    f"Caja '{sesion.caja.nombre}' asignada exitosamente al cajero {nombre_usuario(sesion.cajero)}."
                )
                return redirect('caja:listar_asignaciones')
    else:
        form = AsignarCajeroForm()

    return render(request, 'caja/asignar_cajero.html', {'form': form})


@login_required
def listar_asignaciones_view(request):
    """
    Lista las asignaciones de caja. Los administradores ven todas;
    un cajero ve solo las suyas.
    """
    sesiones = SesionCaja.objects.select_related('caja', 'cajero', 'asignado_por')
    if not request.user.has_perm(PERMISO_ADMIN_CAJAS):
        sesiones = sesiones.filter(cajero=request.user)
    return render(request, 'caja/listar_asignaciones.html', {'sesiones': sesiones})


@login_required
def apertura_caja_view(request):
    """
    SCRUM-37 / SCRUM-40: Pantalla única de apertura y cierre de la caja del cajero.

    Según el turno del cajero autenticado muestra:

    - Turno ASIGNADA: el formulario de apertura, que registra el saldo inicial
      de cada moneda habilitada mediante Movimientos de Caja de APERTURA.
    - Turno ABIERTA: el cierre con arqueo ciego (SCRUM-40); al confirmar se
      registra el arqueo y la caja queda bloqueada.
    - Recién cerrado (`?arqueo=<id>`): el resultado del arqueo.
    - Sin turno: un aviso.
    """
    contexto = {'menu_sections': _menu(request)}

    sesion = SesionCaja.objects.filter(
        cajero=request.user,
        estado=EstadoSesionCaja.ASIGNADA
    ).select_related('caja').first()

    if sesion:
        if request.method == 'POST':
            form = AperturaCajaForm(request.POST)
            if form.is_valid():
                try:
                    sesion = apertura_caja(request.user, form.montos_por_moneda())
                except ValidationError as e:
                    form.add_error(None, e.messages)
                else:
                    messages.success(
                        request,
                        f"Apertura de la caja '{sesion.caja.nombre}' realizada exitosamente. "
                        "Al terminar tu turno, cerrala desde esta misma pantalla."
                    )
                    return redirect('caja:apertura_caja')
        else:
            form = AperturaCajaForm()
        contexto.update({'modo': 'apertura', 'form': form, 'sesion': sesion})
        return render(request, 'caja/apertura_caja.html', contexto)

    arqueo = _arqueo_del_cajero(request)
    if arqueo:
        contexto.update({'modo': 'resultado', 'arqueo': arqueo, 'detalles': arqueo.detalles.all()})
        return render(request, 'caja/apertura_caja.html', contexto)

    try:
        turno = integracion.obtener_turno_abierto(request.user)
        monedas = sorted(integracion.obtener_saldo_registrado(turno)) if turno else []
    except integracion.ModuloCajaNoDisponible:
        contexto['modo'] = 'modulo_no_disponible'
        return render(request, 'caja/apertura_caja.html', contexto)

    if turno is None:
        contexto['modo'] = 'sin_caja'
        return render(request, 'caja/apertura_caja.html', contexto)

    form = CierreCajaForm(request.POST or None, monedas=monedas)
    if request.method == 'POST' and form.is_valid():
        try:
            arqueo = registrar_cierre(request.user, form.saldos_declarados())
        except ValidationError as e:
            form.add_error(None, e.messages)
        except integracion.ModuloCajaNoDisponible:
            contexto['modo'] = 'modulo_no_disponible'
            return render(request, 'caja/apertura_caja.html', contexto)
        else:
            return redirect(f"{reverse('caja:apertura_caja')}?arqueo={arqueo.id}")

    contexto.update({'modo': 'cierre', 'form': form, 'sesion': turno})
    return render(request, 'caja/apertura_caja.html', contexto)


def _menu(request):
    """Devuelve las secciones del menú lateral principal según los roles del usuario."""
    return get_menu_sections(
        resolve_user_role(request), None, is_authenticated=True, roles=resolve_user_roles(request)
    )


def _arqueo_del_cajero(request):
    """Devuelve el arqueo indicado en `?arqueo=<id>` si pertenece al usuario, o `None`."""
    arqueo_id = request.GET.get('arqueo')
    if not arqueo_id:
        return None
    try:
        return ArqueoCaja.objects.filter(id=arqueo_id, cajero=request.user).first()
    except (ValueError, ValidationError):  # id que no es un UUID válido
        return None
