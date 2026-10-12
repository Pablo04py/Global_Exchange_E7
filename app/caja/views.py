from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect

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
