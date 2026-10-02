"""
Módulo de controladores/vistas para la gestión de Medios de Pago (mpagos).

Implementa la lógica del CRUD (Crear, Leer, Modificar, Eliminar) asegurando
que cada cliente acceda e interactúe únicamente con sus propios medios de pago.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from clientes.permisos import obtener_cliente_activo, puede_administrar_cliente
from .models import MedioPago
from .forms import MedioPagoForm

@login_required
def listar_medios_pago(request):
    """
    Vista para consultar y listar todos los medios de pago activos del usuario autenticado.
    """
    cliente = obtener_cliente_activo(request)

    if not cliente:
        messages.warning(request, "Debe seleccionar un cliente para consultar sus medios de pago.")
        return redirect('dashboard')
    
    medios = MedioPago.objects.filter(cliente=cliente, activo=True)
    puede_administrar = puede_administrar_cliente(request, cliente)
    return render(request, 'mpagos/listar.html', {'medios': medios, 'cliente' : cliente, 'puede_administrar' : puede_administrar})


@login_required
def crear_medio_pago(request):
    """
    Registra un medio de pago para el cliente activo.

    La operación solo puede ser realizada por un Administrador General
    o por un usuario con rol local ADMIN en el cliente seleccionado.

    El medio queda asociado al cliente activo y se registra también
    el usuario que realizó la creación.

    Args:
        request:
            Solicitud HTTP de Django.

    Returns:
        HttpResponse:
            Formulario de creación cuando la petición es GET o contiene
            errores de validación.

        HttpResponseRedirect:
            Redirección al listado después de crear correctamente
            el medio de pago.

        HttpResponseForbidden:
            Respuesta 403 si el usuario no puede administrar el cliente.
    """

    cliente = obtener_cliente_activo(request)

    if not cliente:
        messages.warning(request, "Debe seleccionar un cliente.")
        return redirect('dashboard')

    if not puede_administrar_cliente(request, cliente):
        return HttpResponseForbidden("No tiene permisos para agregar medios de pago a este cliente.")

    if request.method == 'POST':
        form = MedioPagoForm(request.POST)
        if form.is_valid():
            medio = form.save(commit=False)
            medio.usuario = request.user
            medio.cliente = cliente

            # Si el nuevo medio se marca como predeterminado, desmarcar los anteriores del mismo usuario
            if medio.es_predeterminado:
                MedioPago.objects.filter(cliente=cliente, activo = True).update(es_predeterminado=False)
            medio.save()
            messages.success(request, "Medio de pago registrado exitosamente.")
            return redirect('mpagos:listar')
    else:
        form = MedioPagoForm()

    return render(request, 'mpagos/form.html', {
        'form': form,
        'cliente' : cliente,
        'titulo': 'Registrar Medio de Pago'
    })


@login_required
def editar_medio_pago(request, pk):
    """
    Vista para modificar los datos de un medio de pago existente perteneciente al cliente activo.
    """
    cliente = obtener_cliente_activo(request)

    if not cliente:
        messages.warning(request,"Debe seleccionar un cliente.")
        return redirect('dashboard')

    if not puede_administrar_cliente(request, cliente):
        return HttpResponseForbidden(
            "No tiene permisos para editar los medios de pago de este cliente.")

    medio = get_object_or_404(MedioPago, pk=pk, cliente=cliente, activo=True)

    if request.method == 'POST':
        form = MedioPagoForm(request.POST, instance=medio)
        if form.is_valid():
            medio_editado = form.save(commit=False)

            medio_editado.cliente = cliente

            if medio_editado.es_predeterminado:
                MedioPago.objects.filter(cliente=cliente, activo=True).exclude(pk=pk).update(es_predeterminado=False)

            medio_editado.save()
            messages.success(request, "Medio de pago actualizado correctamente.")
            return redirect('mpagos:listar')
    else:
        form = MedioPagoForm(instance=medio)

    return render(request, 'mpagos/form.html', {
        'form': form,
        'object': medio,
        'cliente' : cliente,
        'titulo': 'Editar Medio de Pago'
    })


@login_required
def eliminar_medio_pago(request, pk):
    """
    Vista para deshabilitar (borrado lógico) un medio de pago del cliente activo.
    """

    cliente = obtener_cliente_activo(request)

    if not cliente:
        messages.warning(
            request,
            "Debe seleccionar un cliente."
        )
        return redirect('dashboard')

    if not puede_administrar_cliente(request, cliente):
        return HttpResponseForbidden(
            "No tiene permisos para eliminar los medios de pago "
            "de este cliente."
        )
    
    medio = get_object_or_404(MedioPago, pk=pk, cliente=cliente, activo=True)

    if request.method == 'POST':
        medio.activo = False
        medio.save(update_fields=['activo'])

        messages.success(request, "Medio de pago eliminado correctamente.")
        return redirect('mpagos:listar')

    return render(request, 'mpagos/confirmar_eliminar.html', {
        'medio': medio,
        'object': medio,
        'cliente' : cliente
    })