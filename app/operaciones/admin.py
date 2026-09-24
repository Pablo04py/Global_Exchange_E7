from django.contrib import admin
from .models import Moneda, TasaDeCambio

admin.site.register(Moneda)
admin.site.register(TasaDeCambio)