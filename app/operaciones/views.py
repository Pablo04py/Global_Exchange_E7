from django.shortcuts import render, redirect, get_object_or_404
from usuarios.decorators import requiere_rol
from .models import Moneda, TasaDeCambio
from .forms import MonedaForm, TasaDeCambioForm
from decimal import Decimal, InvalidOperation
from .models import TasaDeCambio

@requiere_rol('Administrador General')
def lista_monedas(request):
    monedas = Moneda.objects.all()
    return render(request, 'operaciones/lista_monedas.html', {'monedas': monedas})


@requiere_rol('Administrador General')
def crear_moneda(request):
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
    # Trae la última tasa vigente de cada moneda habilitada
    monedas = Moneda.objects.filter(habilitada=True)
    tasas_actuales = []
    for moneda in monedas:
        ultima_tasa = moneda.tasas.first()  # gracias al ordering
        tasas_actuales.append({'moneda': moneda, 'tasa': ultima_tasa})
    return render(request, 'operaciones/lista_tasas.html', {'tasas_actuales': tasas_actuales})


@requiere_rol('Analista Cambiario', 'Administrador General')
def crear_tasa(request, moneda_id=None):
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


