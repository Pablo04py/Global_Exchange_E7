from django.shortcuts import render

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Caja, SesionCaja, EstadoSesionCaja
from .forms import AsignarCajeroForm


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