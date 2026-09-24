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
]
