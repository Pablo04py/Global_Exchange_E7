from django.shortcuts import render
from django.http import JsonResponse
from .models import Cotizacion  # Verifica que tu modelo se llame Cotizacion

def ver_cotizaciones(request):
    try:
        # Consulta optimizada para PostgreSQL (una fila por moneda)
        cotizaciones = Cotizacion.objects.order_by('moneda', '-id').distinct('moneda')
    except Exception as e:
        print(f"Error consultando cotizaciones: {e}")
        cotizaciones = []

    return render(request, 'cotizaciones/lista.html', {'cotizaciones': cotizaciones})


def api_cotizaciones(request):
    try:
        cotizaciones = Cotizacion.objects.order_by('moneda', '-id').distinct('moneda')
        data = []
        for c in cotizaciones:
            data.append({
                'moneda': getattr(c, 'moneda', ''),
                'compra': str(getattr(c, 'compra', getattr(c, 'precio_compra', '0'))),
                'venta': str(getattr(c, 'venta', getattr(c, 'precio_venta', '0'))),
            })
        return JsonResponse({'cotizaciones': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)