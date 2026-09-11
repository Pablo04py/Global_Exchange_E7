"""
Módulo de controladores/vistas para la gestión de Medios de Pago (mpagos).

Implementa la lógica del CRUD (Crear, Leer, Modificar, Eliminar) asegurando
que cada cliente acceda e interactúe únicamente con sus propios medios de pago.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import MedioPago
from .forms import MedioPagoForm


@login_required
def listar_medios_pago(request):
    """
    Vista para consultar y listar todos los medios de pago activos del usuario autenticado.
    """
    medios = MedioPago.objects.filter(usuario=request.user, activo=True)
    return render(request, 'mpagos/listar.html', {'medios': medios})


@login_required
def crear_medio_pago(request):
    """
    Vista para registrar un nuevo medio de pago asignado al usuario en sesión.
    """
    if request.method == 'POST':
        form = MedioPagoForm(request.POST)
        if form.is_valid():
            medio = form.save(commit=False)
            medio.usuario = request.user

            # Si el nuevo medio se marca como predeterminado, desmarcar los anteriores del mismo usuario
            if medio.es_predeterminado:
                MedioPago.objects.filter(usuario=request.user).update(es_predeterminado=False)

            medio.save()
            messages.success(request, "Medio de pago registrado exitosamente.")
            return redirect('mpagos:listar')
    else:
        form = MedioPagoForm()

    return render(request, 'mpagos/form.html', {
        'form': form,
        'titulo': 'Registrar Medio de Pago'
    })


@login_required
def editar_medio_pago(request, pk):
    """
    Vista para modificar los datos de un medio de pago existente perteneciente al usuario.
    """
    medio = get_object_or_404(MedioPago, pk=pk, usuario=request.user, activo=True)

    if request.method == 'POST':
        form = MedioPagoForm(request.POST, instance=medio)
        if form.is_valid():
            medio_editado = form.save(commit=False)

            if medio_editado.es_predeterminado:
                MedioPago.objects.filter(usuario=request.user).exclude(pk=pk).update(es_predeterminado=False)

            medio_editado.save()
            messages.success(request, "Medio de pago actualizado correctamente.")
            return redirect('mpagos:listar')
    else:
        form = MedioPagoForm(instance=medio)

    return render(request, 'mpagos/form.html', {
        'form': form,
        'object': medio,
        'titulo': 'Editar Medio de Pago'
    })


@login_required
def eliminar_medio_pago(request, pk):
    """
    Vista para deshabilitar (borrado lógico) un medio de pago del usuario en sesión.
    """
    medio = get_object_or_404(MedioPago, pk=pk, usuario=request.user, activo=True)

    if request.method == 'POST':
        medio.activo = False
        medio.save()

        messages.success(request, "Medio de pago eliminado correctamente.")
        return redirect('mpagos:listar')

    return render(request, 'mpagos/confirmar_eliminar.html', {
        'medio': medio,
        'object': medio
    })