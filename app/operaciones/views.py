"""Vistas de la aplicación operaciones (monedas, tasas de cambio, simulador e historial de transacciones)."""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_GET
from clientes.models import Cliente
from main.views import get_menu_sections, resolve_user_role
from usuarios.decorators import requiere_rol
from .models import Moneda, TasaDeCambio, Transaccion
from .forms import FiltroHistorialForm, MonedaForm, TasaDeCambioForm
from decimal import Decimal, InvalidOperation
from .models import TasaDeCambio

@requiere_rol('Administrador General')
def lista_monedas(request):
    """Lista todas las monedas registradas.

    Solo para el rol `Administrador General`.

    Args:
        request: Petición HTTP.

    Returns:
        HttpResponse: Plantilla `operaciones/lista_monedas.html`.
    """
    monedas = Moneda.objects.all()
    return render(request, 'operaciones/lista_monedas.html', {'monedas': monedas})


@requiere_rol('Administrador General')
def crear_moneda(request):
    """Muestra y procesa el formulario de alta de una moneda.

    Solo para el rol `Administrador General`. Al guardar, redirige a la
    carga de la tasa de cambio inicial de la nueva moneda.

    Args:
        request: Petición HTTP.

    Returns:
        HttpResponse: Formulario o redirección a `crear_tasa_con_moneda`.
    """
    if request.method == 'POST':
        form = MonedaForm(request.POST)
        if form.is_valid():
            moneda = form.save()
            return redirect('crear_tasa_con_moneda', moneda_id=moneda.id)
    else:
        form = MonedaForm()
    return render(request, 'operaciones/form_moneda.html', {'form': form})


@requiere_rol('Administrador General')
def editar_moneda(request, moneda_id):
    """Muestra y procesa el formulario de edición de una moneda.

    Solo para el rol `Administrador General`.

    Args:
        request: Petición HTTP.
        moneda_id: UUID de la moneda a editar.

    Returns:
        HttpResponse: Formulario o redirección a `lista_monedas`.

    Raises:
        Http404: Si la moneda no existe.
    """
    moneda = get_object_or_404(Moneda, id=moneda_id)
    if request.method == 'POST':
        form = MonedaForm(request.POST, instance=moneda)
        if form.is_valid():
            form.save()
            return redirect('lista_monedas')
    else:
        form = MonedaForm(instance=moneda)
    return render(request, 'operaciones/form_moneda.html', {'form': form})


#tasa de cambio 


@requiere_rol('Analista Cambiario', 'Administrador General')
def lista_tasas(request):
    """Lista la tasa vigente (la más reciente) de cada moneda habilitada.

    Para los roles `Analista Cambiario` y `Administrador General`.

    Args:
        request: Petición HTTP.

    Returns:
        HttpResponse: Plantilla `operaciones/lista_tasas.html`.
    """
    # Trae la última tasa vigente de cada moneda habilitada
    monedas = Moneda.objects.filter(habilitada=True)
    tasas_actuales = []
    for moneda in monedas:
        ultima_tasa = moneda.tasas.first()  # gracias al ordering
        tasas_actuales.append({'moneda': moneda, 'tasa': ultima_tasa})
    return render(request, 'operaciones/lista_tasas.html', {'tasas_actuales': tasas_actuales})


@requiere_rol('Analista Cambiario', 'Administrador General')
def crear_tasa(request, moneda_id=None):
    """Muestra y procesa el formulario de una nueva tasa de cambio.

    Para los roles `Analista Cambiario` y `Administrador General`.

    Args:
        request: Petición HTTP.
        moneda_id: UUID de la moneda a preseleccionar en el formulario (opcional).

    Returns:
        HttpResponse: Formulario o redirección a `lista_tasas`.
    """
    # Si viene un moneda_id por la URL, buscamos la moneda. Si no, queda en None.
    moneda_inicial = get_object_or_404(Moneda, id=moneda_id) if moneda_id else None

    if request.method == 'POST':
        form = TasaDeCambioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_tasas')
    else:
        form = TasaDeCambioForm(initial={'moneda': moneda_inicial} if moneda_inicial else None)

    return render(request, 'operaciones/form_tasa.html', {'form': form})

def simular(request):
    """Simulador de conversión de una moneda extranjera a guaraníes (PYG).

    Lee de la query string `monto`, `tasa_id` y `tipo_operacion`
    (`compra` o `venta`) y calcula el monto resultante con el precio
    de compra o de venta de la tasa elegida. Es de acceso público.

    Args:
        request: Petición HTTP (GET).

    Returns:
        HttpResponse: Plantilla `operaciones/simulador.html` con el resultado
        o un mensaje de error si los datos no son válidos.
    """

    resultado = None
    monto_ingresado = request.GET.get('monto', '')
    tasa_id = request.GET.get('tasa_id', '')
    tipo_op = request.GET.get('tipo_operacion', 'compra')

    #Obtener las divisas
    tasas = TasaDeCambio.objects.select_related('moneda').filter(
        moneda__habilitada=True
    ).order_by('-fecha_vigencia')

    if monto_ingresado and tasa_id:
        try:
            monto = Decimal(monto_ingresado)
            tasa = TasaDeCambiotasa = TasaDeCambio.objects.get(id=tasa_id)
            
            # Ejecución de los métodos definidos en la entidad TasaDeCambio
            if tipo_op == 'compra':
                precio_aplicado = tasa.calcular_precio_compra()
            else:
                precio_aplicado = tasa.calcular_precio_venta()

            monto_destino = monto * precio_aplicado

            resultado = {
                'monto_origen': monto,
                'monto_destino': monto_destino,
                'precio_aplicado': precio_aplicado,
                'moneda_origen': tasa.moneda.codigo,
                'moneda_destino': 'PYG',
                'tipo_operacion': tipo_op,
            }
        except (InvalidOperation, TasaDeCambio.DoesNotExist):
            resultado = {'error': 'Por favor ingrese un monto y una tasa de cambio válidos.'}

    context = {
        'tasas': tasas,
        'resultado': resultado,
        'monto_input': monto_ingresado,
        'tasa_id_sel': tasa_id,
        'tipo_op_sel': tipo_op,
    }
    return render(request, 'operaciones/simulador.html', context)


TRANSACCIONES_POR_PAGINA = 20
# Páginas visibles alrededor de la actual y en cada extremo; el resto se abrevia con "…"
PAGINAS_A_CADA_LADO = 2
PAGINAS_EN_EXTREMOS = 1


@login_required
@require_GET
def historial_transacciones(request):
    """Lista, en modo solo lectura, las transacciones del usuario autenticado.

    Acceso: usuario autenticado registrado como cliente (con un `Cliente`
    asociado). Si no lo está, se lo redirige a `convertirse_en_cliente`.
    Un usuario anónimo es redirigido al login.

    El cliente es el propio usuario, por lo que solo se muestran las
    transacciones cuyo `usuario` es el usuario autenticado; nunca se exponen
    operaciones de otros usuarios. La vista solo acepta GET: no crea,
    modifica ni elimina transacciones.

    Los filtros llegan por query string (ver `FiltroHistorialForm`) y el
    resultado se pagina de a `TRANSACCIONES_POR_PAGINA`, de la más reciente
    a la más antigua. `rango_paginas` contiene los números de página a
    mostrar, abreviados con `Paginator.ELLIPSIS` cuando hay muchas.

    Args:
        request: Petición HTTP (GET con filtros opcionales y `page`).

    Returns:
        HttpResponse: Plantilla `operaciones/historial.html`, o redirección a
        `convertirse_en_cliente`.
    """
    # Se revisará cuando se configuren las categorías de cliente (Minorista, Mayorista, VIP, Corporativo)
    if not Cliente.objects.filter(usuarios_asociados__usuario=request.user).exists():
        return redirect('convertirse_en_cliente')

    # Límite de seguridad: solo transacciones del usuario autenticado
    transacciones = Transaccion.objects.filter(usuario=request.user).select_related(
        'moneda', 'medio_pago', 'cajero'
    )

    form = FiltroHistorialForm(request.GET or None, transacciones=transacciones)
    if form.is_bound:
        form.is_valid()  # completa cleaned_data; los campos con error se ignoran al filtrar
    filtradas = form.filtrar(transacciones).order_by('-fecha')

    page_obj = Paginator(filtradas, TRANSACCIONES_POR_PAGINA).get_page(request.GET.get('page'))

    context = {
        'form': form,
        'page_obj': page_obj,
        'rango_paginas': list(page_obj.paginator.get_elided_page_range(
            page_obj.number, on_each_side=PAGINAS_A_CADA_LADO, on_ends=PAGINAS_EN_EXTREMOS
        )),
        'total': page_obj.paginator.count,
        'hay_filtros': any(v for k, v in request.GET.items() if k != 'page'),
        'menu_sections': get_menu_sections(resolve_user_role(request), None, is_authenticated=True),
    }
    return render(request, 'operaciones/historial.html', context)
