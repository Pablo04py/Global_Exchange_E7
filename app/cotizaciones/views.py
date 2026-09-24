from django.shortcuts import render
from django.http import JsonResponse
from operaciones.models import Moneda, TasaDeCambio

def ver_cotizaciones(request):
    """Obtiene las monedas habilitadas y les adjunta su última cotización vigente."""
    monedas = Moneda.objects.filter(habilitada=True)
    cotizaciones = []

    for moneda in monedas:
        # Busca la última tasa de cambio registrada para esta moneda
        ultima_tasa = TasaDeCambio.objects.filter(moneda=moneda).order_by('-fecha_vigencia').first()

        if ultima_tasa:
            precio_compra = ultima_tasa.calcular_precio_compra()
            precio_venta = ultima_tasa.calcular_precio_venta()
        else:
            precio_compra = "0"
            precio_venta = "0"

        cotizaciones.append({
            'moneda': moneda.codigo,
            'precio_compra': precio_compra,
            'precio_venta': precio_venta,
        })

    return render(request, 'cotizaciones/lista.html', {'cotizaciones': cotizaciones})


def api_cotizaciones(request):
    """Endpoint JSON compatible con la vista de cotizaciones."""
    try:
        monedas = Moneda.objects.filter(habilitada=True)
        data = []

        for moneda in monedas:
            ultima_tasa = TasaDeCambio.objects.filter(moneda=moneda).order_by('-fecha_vigencia').first()
            data.append({
                'moneda': moneda.codigo,
                'compra': str(ultima_tasa.calcular_precio_compra()) if ultima_tasa else "0",
                'venta': str(ultima_tasa.calcular_precio_venta()) if ultima_tasa else "0",
            })

        return JsonResponse({'cotizaciones': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)