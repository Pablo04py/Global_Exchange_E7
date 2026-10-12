"""
Módulo de controladores/vistas para la gestión de Medios de Pago (mpagos).

Implementa la lógica del CRUD (Crear, Leer, Modificar, Eliminar) asegurando
que cada cliente acceda e interactúe únicamente con sus propios medios de pago.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from clientes.permisos import obtener_cliente_activo, puede_administrar_cliente
from .models import MedioPago
from .forms import MedioPagoForm
from django.views.decorators.http import  require_GET, require_POST

from .stripe_service import crear_setup_intent_tarjeta, obtener_tarjeta_confirmada

from django.conf import settings
from django.db import transaction

from django.core.exceptions import ValidationError

@login_required
def listar_medios_pago(request):
    """
    Vista para consultar y listar todos los medios de pago activos del usuario autenticado.
    """
    cliente = obtener_cliente_activo(request)

    if not cliente:
        messages.warning(request, "Debe seleccionar un cliente para consultar sus medios de pago.")
        return redirect('dashboard')
    
    medios = (MedioPago.objects.filter(cliente=cliente, activo=True).exclude(tipo='EFECTIVO'))
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

        # Las tarjetas se registrane exclusivamente mediante Stripe Elements

        if request.POST.get('tipo') == 'TARJETA':
             
            form = MedioPagoForm(request.POST)

            form.add_error(None, "Las tarjetas deben registrarse mediante el formulario seguro")

        else:

            form = MedioPagoForm(request.POST)

            if form.is_valid():
                medio = form.save(commit=False)
                medio.usuario = request.user
                medio.cliente = cliente

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
        'titulo': 'Registrar Medio de Pago',
        'stripe_publishable_key': (settings.STRIPE_PUBLISHABLE_KEY),
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

    medio = get_object_or_404(MedioPago, pk=pk, cliente=cliente, activo=True, tipo__in=['TARJETA','SIPAP'])

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
    
    medio = get_object_or_404(MedioPago, pk=pk, cliente=cliente, activo=True, tipo__in=['TARJETA','SIPAP'])

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

@login_required
@require_POST
def crear_setup_intent(request):
    """
    Crea un SetupIntent de Stripe para registrar
    una tarjeta del cliente activo.
    """

    cliente = obtener_cliente_activo(request)

    if not cliente:
        return JsonResponse(
            {
                'error': (
                    'Debe seleccionar un cliente.'
                )
            },
            status=400
        )

    if not puede_administrar_cliente(
        request,
        cliente
    ):
        return JsonResponse(
            {
                'error': (
                    'No tiene permisos para registrar '
                    'tarjetas para este cliente.'
                )
            },
            status=403
        )

    try:
        setup_intent = crear_setup_intent_tarjeta(
            cliente
        )

        return JsonResponse(
            {
                'client_secret':
                    setup_intent.client_secret
            }
        )

    except Exception as error:

        print(
            "ERROR SETUP INTENT STRIPE:",
            type(error).__name__,
            repr(error),
            flush=True
        )

        return JsonResponse(
            {
                'error': (
                    'No se pudo iniciar el registro '
                    'seguro de la tarjeta.'
                )
            },
            status=500
        )


@login_required
@require_GET
def stripe_registro_retorno(request):
    """
    Procesa el regreso desde Stripe luego de configurar
    correctamente una tarjeta.
    """

    cliente = obtener_cliente_activo(request)

    if not cliente:
        messages.warning(
            request,
            "Debe seleccionar un cliente."
        )
        return redirect('dashboard')

    if not puede_administrar_cliente(
        request,
        cliente
    ):
        return HttpResponseForbidden(
            "No tiene permisos para registrar "
            "tarjetas para este cliente."
        )

    setup_intent_id = request.GET.get(
        'setup_intent'
    )

    if not setup_intent_id:
        messages.error(
            request,
            "No se recibió la confirmación de Stripe."
        )
        return redirect('mpagos:crear')

    try:
        payment_method = obtener_tarjeta_confirmada(
            cliente,
            setup_intent_id
        )

        card = payment_method.card

        predeterminado = (
            request.GET.get('predeterminado')
            == '1'
        )

        nombre_titular = (
            payment_method.billing_details.name
            or cliente.nombre_o_denominacion
        )

        with transaction.atomic():

            existente = MedioPago.objects.filter(
                stripe_payment_method_id=(
                    payment_method.id
                )
            ).first()

            if existente:

                if existente.cliente_id != cliente.id:
                    raise ValidationError(
                        "La tarjeta ya se encuentra "
                        "asociada a otro cliente."
                    )

                existente.activo = True
                existente.nombre_titular = (
                    nombre_titular
                )
                existente.numero_enmascarado = (
                    f"**** **** **** {card.last4}"
                )
                existente.marca_tarjeta = (
                    card.brand
                )
                existente.exp_mes = (
                    card.exp_month
                )
                existente.exp_anio = (
                    card.exp_year
                )
                existente.es_predeterminado = (
                    predeterminado
                )

                medio = existente

            else:

                medio = MedioPago(
                    usuario=request.user,
                    cliente=cliente,
                    tipo='TARJETA',
                    nombre_titular=nombre_titular,
                    banco_emisor=None,
                    numero_enmascarado=(
                        f"**** **** **** "
                        f"{card.last4}"
                    ),
                    stripe_payment_method_id=(
                        payment_method.id
                    ),
                    marca_tarjeta=card.brand,
                    exp_mes=card.exp_month,
                    exp_anio=card.exp_year,
                    es_predeterminado=(
                        predeterminado
                    ),
                    activo=True,
                )

            if predeterminado:
                MedioPago.objects.filter(
                    cliente=cliente,
                    activo=True
                ).exclude(
                    stripe_payment_method_id=(
                        payment_method.id
                    )
                ).update(
                    es_predeterminado=False
                )

            medio.save()

        messages.success(
            request,
            "Tarjeta registrada correctamente."
        )

        return redirect('mpagos:listar')

    except ValidationError as error:

        mensaje = (
            error.message
            if hasattr(error, 'message')
            else str(error)
        )

        messages.error(
            request,
            mensaje
        )

    except Exception as error:

        print(
            "ERROR REGISTRO TARJETA STRIPE:",
            type(error).__name__,
            repr(error),
            flush=True
        )

        messages.error(
            request,
            "No se pudo completar el registro "
            "de la tarjeta."
        )

    return redirect('mpagos:crear')