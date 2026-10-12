"""Servicios para creación y distribución de notificaciones."""

from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Notificacion, NotificacionUsuario


@transaction.atomic
def crear_notificacion_cambio_tasa(
    *,
    tasa_nueva,
    tasa_anterior=None,
    usuario=None
):
    """
    Crea una notificación cuando se registra una nueva tasa de cambio
    y la distribuye a todos los usuarios activos del sistema.

    Args:
        tasa_nueva:
            Nueva instancia de TasaDeCambio registrada.

        tasa_anterior:
            Tasa vigente inmediatamente anterior para la misma moneda.
            Puede ser None si es la primera tasa registrada.

        usuario:
            Usuario que realizó el cambio.
    """

    moneda = tasa_nueva.moneda.codigo

    compra_nueva = tasa_nueva.calcular_precio_compra()
    venta_nueva = tasa_nueva.calcular_precio_venta()

    if tasa_anterior:
        compra_anterior = tasa_anterior.calcular_precio_compra()
        venta_anterior = tasa_anterior.calcular_precio_venta()

        titulo = f"Cotización {moneda} actualizada"

        mensaje = (
            f"Compra: G. {compra_anterior:,.2f} → "
            f"G. {compra_nueva:,.2f}\n"
            f"Venta: G. {venta_anterior:,.2f} → "
            f"G. {venta_nueva:,.2f}"
        )

    else:
        titulo = f"Nueva cotización disponible: {moneda}"

        mensaje = (
            f"Compra: G. {compra_nueva:,.2f}\n"
            f"Venta: G. {venta_nueva:,.2f}"
        )

    notificacion = Notificacion.objects.create(
        tipo=Notificacion.Tipo.TASA_CAMBIO,
        titulo=titulo,
        mensaje=mensaje,
        creada_por=usuario
    )

    Usuario = get_user_model()

    usuarios = Usuario.objects.filter(
        is_active=True
    )

    destinatarios = [
        NotificacionUsuario(
            notificacion=notificacion,
            usuario=destinatario
        )
        for destinatario in usuarios
    ]

    NotificacionUsuario.objects.bulk_create(destinatarios)

    return notificacion