from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect

from .models import SesionCaja, EstadoSesionCaja
from .forms import AsignarCajeroForm, AperturaCajaForm, CierreCajaForm
from .services import (
    asignar_cajero, apertura_caja, cerrar_caja, saldo_por_moneda, nombre_usuario,
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
    SCRUM-37: Permite al cajero autenticado registrar el saldo inicial
    para todas las monedas habilitadas mediante Movimientos de Caja de APERTURA.
    """
    sesion = SesionCaja.objects.filter(
        cajero=request.user,
        estado=EstadoSesionCaja.ASIGNADA
    ).select_related('caja').first()

    if not sesion:
        messages.error(request, "No tienes ninguna caja asignada pendiente de apertura.")
        return redirect('caja:listar_asignaciones')

    if request.method == 'POST':
        form = AperturaCajaForm(request.POST)
        if form.is_valid():
            try:
                sesion = apertura_caja(request.user, form.montos_por_moneda())
            except ValidationError as e:
                messages.error(request, ' '.join(e.messages))
                return redirect('caja:listar_asignaciones')

            messages.success(request, f"Apertura de la caja '{sesion.caja.nombre}' realizada exitosamente.")
            return redirect('caja:listar_asignaciones')
    else:
        form = AperturaCajaForm()

    return render(request, 'caja/apertura_caja.html', {
        'form': form,
        'sesion': sesion,
    })


@login_required
def cerrar_caja_view(request):
    """
    Cierre/arqueo: el cajero declara lo que contó por moneda y el sistema
    lo compara contra el saldo calculado desde MovimientoCaja.
    """
    sesion = SesionCaja.objects.filter(
        cajero=request.user,
        estado=EstadoSesionCaja.ABIERTA
    ).select_related('caja').first()

    if not sesion:
        messages.error(request, "No tienes ninguna caja abierta para cerrar.")
        return redirect('caja:listar_asignaciones')

    codigos = list(saldo_por_moneda(sesion).keys())

    if request.method == 'POST':
        form = CierreCajaForm(request.POST, codigos_extra=codigos)
        if form.is_valid():
            try:
                sesion, arqueos = cerrar_caja(request.user, form.montos_por_moneda())
            except ValidationError as e:
                messages.error(request, ' '.join(e.messages))
                return redirect('caja:listar_asignaciones')

            messages.success(request, f"Caja '{sesion.caja.nombre}' cerrada correctamente.")
            for arqueo in arqueos:
                if arqueo.diferencia != 0:
                    messages.warning(
                        request,
                        f"{arqueo.moneda}: {arqueo.resultado} de {abs(arqueo.diferencia)}."
                    )
            return redirect('caja:listar_asignaciones')
    else:
        form = CierreCajaForm(codigos_extra=codigos)

    return render(request, 'caja/cerrar_caja.html', {
        'form': form,
        'sesion': sesion,
    })