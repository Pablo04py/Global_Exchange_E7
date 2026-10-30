from django.urls import path

from . import views


app_name = 'facturacion'


urlpatterns = [
    path(
        '<uuid:factura_id>/kude/',
        views.descargar_kude,
        name='descargar_kude',
    ),
    path(
        '<uuid:factura_id>/xml/',
        views.descargar_xml,
        name='descargar_xml',
    ),
]