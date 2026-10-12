"""Rutas de la aplicación operaciones (monedas, tasas, simulador e historial)."""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_monedas, name='lista_monedas'),
    path('crear/', views.crear_moneda, name='crear_moneda'),
    path('<uuid:moneda_id>/editar/', views.editar_moneda, name='editar_moneda'),
    path('tasas/', views.lista_tasas, name='lista_tasas'),
    path('tasas/crear/', views.crear_tasa, name='crear_tasa'),
    path('tasas/crear/<uuid:moneda_id>/', views.crear_tasa, name='crear_tasa_con_moneda'),
    path('simulador/', views.simular, name='simulador'),
    path('historial/', views.historial_transacciones, name='historial_transacciones'),
    path('operar/', views.operar, name='operar'),
    path('operar/<uuid:transaccion_id>/', views.detalle_transaccion, name='detalle_transaccion'),
    path('operar/<uuid:transaccion_id>/pagar/stripe/',views.iniciar_pago_stripe,name='iniciar_pago_stripe'),
    path('pagos/stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('operar/<uuid:transaccion_id>/pago/estado/', views.estado_pago_stripe, name='estado_pago_stripe'),
    path('operar/<uuid:transaccion_id>/pagar/sipap/', views.confirmar_pago_sipap, name='confirmar_pago_sipap'),
    path('operar/<uuid:transaccion_id>/pagar/efectivo/', views.confirmar_pago_efectivo, name='confirmar_pago_efectivo'),
]
