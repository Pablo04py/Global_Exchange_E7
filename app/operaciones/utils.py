"""Funciones auxiliares de la aplicación operaciones."""

from .models import Transaccion

# Orden importante: el User-Agent de iPhone/iPad incluye "Mac OS X"
# y el de Android incluye "Linux", por eso se evalúan primero.
_PATRONES_DISPOSITIVO = [
    ('iphone', Transaccion.Dispositivo.IPHONE),
    ('ipad', Transaccion.Dispositivo.IPAD),
    ('android', Transaccion.Dispositivo.ANDROID),
    ('windows', Transaccion.Dispositivo.WINDOWS),
    ('macintosh', Transaccion.Dispositivo.MAC),
    ('mac os x', Transaccion.Dispositivo.MAC),
    ('linux', Transaccion.Dispositivo.LINUX),
]


def detectar_dispositivo(request):
    """Identifica el tipo de dispositivo a partir del User-Agent de la petición.

    Pensada para usarse al registrar una `Transaccion` desde la pantalla de
    compra/venta, guardando el resultado en `Transaccion.dispositivo`.

    Args:
        request: Petición HTTP (se lee la cabecera `User-Agent`).

    Returns:
        str: Un valor de `Transaccion.Dispositivo`; `OTRO` si no se reconoce.
    """
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    for patron, dispositivo in _PATRONES_DISPOSITIVO:
        if patron in user_agent:
            return dispositivo
    return Transaccion.Dispositivo.OTRO
