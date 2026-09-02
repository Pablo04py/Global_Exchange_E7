from django.shortcuts import render
from django.http import JsonResponse
from .models import Cotizacion

def ver_cotizaciones(request):
    cotizaciones = Cotizacion.objects.all()
    return render(request, 'cotizaciones/lista.html', {'cotizaciones': cotizaciones})

def api_cotizaciones(request):
    data = list(Cotizacion.objects.values('moneda', 'precio_compra', 'precio_venta'))
    return JsonResponse({'cotizaciones': data})