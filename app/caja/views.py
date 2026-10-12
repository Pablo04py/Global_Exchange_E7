from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction

from .models import (
    Caja, SesionCaja, EstadoSesionCaja, EstadoCaja, 
    MovimientoCaja, SentidoMovimiento, TipoMovimiento
)
from .forms import AsignarCajeroForm, AperturaCajaForm
from operaciones.models import Moneda


@login_required
def asignar_cajero_view(request):
    """
    SCRUM-36: Permite a un administrador asignar una caja disponible a un cajero.
    """
    if request.method == 'POST':
        form = AsignarCajeroForm(request.POST)
        if form.is_valid():
            sesion = form.save(commit=False)
            sesion.asignado_por = request.user
            sesion.estado = EstadoSesionCaja.ASIGNADA
            sesion.save()

            messages.success(
                request, 
                f"Caja '{sesion.caja.nombre}' asignada exitosamente al cajero {sesion.cajero.username}."
            )
            return redirect('caja:listar_asignaciones')
    else:
        form = AsignarCajeroForm()

    return render(request, 'caja/asignar_cajero.html', {'form': form})


@login_required
def listar_asignaciones_view(request):
    """
    Lista las asignaciones de caja existentes.
    """
    sesiones = SesionCaja.objects.select_related('caja', 'cajero', 'asignado_por').all()
    return render(request, 'caja/listar_asignaciones.html', {'sesiones': sesiones})


@login_required
def aperturar_caja_view(request):
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
            monedas = Moneda.objects.filter(habilitada=True)
            monto_pyg_inicial = 0.00

            # Usamos transacciones para que no queden datos a medias en caso de error
            with transaction.atomic():
                for moneda in monedas:
                    field_name = f'monto_{moneda.codigo.lower()}'
                    monto = form.cleaned_data.get(field_name, 0.00)

                    # Solo creamos el movimiento si el monto es mayor a 0 (por el validador MinValue)
                    if monto and monto > 0:
                        MovimientoCaja.objects.create(
                            sesion=sesion,
                            moneda=moneda.codigo,  # Guardamos el string (ej. 'PYG'), no el objeto
                            monto=monto,
                            sentido=SentidoMovimiento.ENTRADA,
                            tipo=TipoMovimiento.APERTURA,
                            justificacion=f"Fondo inicial de apertura en {moneda.codigo}"
                        )

                    # Mantenemos esto por compatibilidad con la info visual de la sesión
                    if moneda.codigo.upper() == 'PYG':
                        monto_pyg_inicial = monto

                # Actualizar estado de la sesión y caja
                sesion.monto_inicial = monto_pyg_inicial
                sesion.estado = EstadoSesionCaja.ABIERTA
                sesion.fecha_apertura = timezone.now()
                sesion.save()

                caja = sesion.caja
                caja.estado = EstadoCaja.EN_USO
                caja.save()

            messages.success(request, f"Apertura de la caja '{caja.nombre}' realizada exitosamente.")
            return redirect('caja:listar_asignaciones')
    else:
        form = AperturaCajaForm()

    return render(request, 'caja/aperturar_caja.html', {
        'form': form,
        'sesion': sesion
    })