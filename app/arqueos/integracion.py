"""Punto de conexión del arqueo con el módulo de caja de otras historias.

El cierre de caja (SCRUM-40) necesita datos que implementan otras historias:

- SCRUM-36 / SCRUM-37 (asignación y apertura): el modelo de caja, la caja
  asignada al cajero y su estado.
- Saldo registrado: cuánto debería haber en la caja por moneda.

Este módulo concentra esa dependencia. Los nombres se leen de `settings` (con
los valores por defecto de abajo), así que, si las otras historias usan otros
nombres, se ajusta la configuración sin tocar la lógica del arqueo:

| Setting                     | Por defecto                        | Significado                                |
|-----------------------------|------------------------------------|--------------------------------------------|
| `ARQUEO_MODELO_CAJA`        | `'caja.Caja'`                      | Modelo de caja, como `app.Modelo`          |
| `ARQUEO_CAMPO_CAJERO`       | `'cajero'`                         | Campo de la caja con el cajero asignado    |
| `ARQUEO_CAMPO_ESTADO`       | `'estado'`                         | Campo de la caja con su estado             |
| `ARQUEO_CAMPO_SUCURSAL`     | `'sucursal'`                       | Campo de la caja con su sucursal           |
| `ARQUEO_ESTADO_ABIERTA`     | `'ABIERTA'`                        | Valor del estado de una caja abierta       |
| `ARQUEO_ESTADO_BLOQUEADA`   | `'BLOQUEADA'`                      | Valor que se asigna al cerrar la caja      |
| `ARQUEO_FUNCION_SALDO`      | `'caja.services.saldo_registrado'` | Función `f(caja) -> {codigo_moneda: monto}`|

Mientras esas piezas no existan, las funciones lanzan `ModuloCajaNoDisponible`
y la vista de cierre muestra un aviso en lugar de fallar.
"""

from decimal import Decimal

from django.apps import apps
from django.conf import settings
from django.core.exceptions import FieldError
from django.utils.module_loading import import_string

CONFIGURACION_POR_DEFECTO = {
    'ARQUEO_MODELO_CAJA': 'caja.Caja',
    'ARQUEO_CAMPO_CAJERO': 'cajero',
    'ARQUEO_CAMPO_ESTADO': 'estado',
    'ARQUEO_CAMPO_SUCURSAL': 'sucursal',
    'ARQUEO_ESTADO_ABIERTA': 'ABIERTA',
    'ARQUEO_ESTADO_BLOQUEADA': 'BLOQUEADA',
    'ARQUEO_FUNCION_SALDO': 'caja.services.saldo_registrado',
}


class ModuloCajaNoDisponible(Exception):
    """El modelo de caja o la función de saldo registrado aún no existen o están mal configurados."""


def _config(nombre):
    """Devuelve el valor de un setting de integración o su valor por defecto.

    Args:
        nombre: Nombre del setting (ver `CONFIGURACION_POR_DEFECTO`).

    Returns:
        str: Valor configurado.
    """
    return getattr(settings, nombre, CONFIGURACION_POR_DEFECTO[nombre])


def modelo_caja():
    """Devuelve el modelo de caja configurado.

    Returns:
        type[Model]: Clase del modelo de caja.

    Raises:
        ModuloCajaNoDisponible: Si el modelo no existe.
    """
    try:
        return apps.get_model(_config('ARQUEO_MODELO_CAJA'))
    except (LookupError, ValueError) as error:
        raise ModuloCajaNoDisponible(
            f"El modelo de caja '{_config('ARQUEO_MODELO_CAJA')}' no está disponible."
        ) from error


def obtener_caja_abierta(cajero, bloquear_fila=False):
    """Devuelve la caja asignada al cajero que está abierta.

    Args:
        cajero: Usuario con rol Cajero.
        bloquear_fila: Si es `True`, bloquea la fila (`SELECT ... FOR UPDATE`)
            para evitar dos cierres simultáneos; usar dentro de una transacción.

    Returns:
        Model | None: La caja abierta asignada, o `None` si no tiene ninguna.

    Raises:
        ModuloCajaNoDisponible: Si el modelo o sus campos no están disponibles.
    """
    Caja = modelo_caja()
    filtros = {
        _config('ARQUEO_CAMPO_CAJERO'): cajero,
        _config('ARQUEO_CAMPO_ESTADO'): _config('ARQUEO_ESTADO_ABIERTA'),
    }
    consulta = Caja.objects.select_for_update() if bloquear_fila else Caja.objects.all()
    try:
        return consulta.filter(**filtros).first()
    except FieldError as error:  # campo de cajero o estado mal configurado
        raise ModuloCajaNoDisponible(f"No se pudo consultar la caja: {error}") from error


def obtener_saldo_registrado(caja):
    """Devuelve el saldo registrado (esperado) de la caja por moneda.

    Args:
        caja: Caja abierta.

    Returns:
        dict[str, Decimal]: Saldo por código de moneda, ej. `{'PYG': Decimal('5740000')}`.

    Raises:
        ModuloCajaNoDisponible: Si la función de saldo no existe.
    """
    try:
        funcion = import_string(_config('ARQUEO_FUNCION_SALDO'))
    except ImportError as error:
        raise ModuloCajaNoDisponible(
            f"La función de saldo registrado '{_config('ARQUEO_FUNCION_SALDO')}' no está disponible."
        ) from error
    return {str(moneda).upper(): Decimal(str(monto)) for moneda, monto in funcion(caja).items()}


def datos_de_caja(caja):
    """Toma la "foto" de la caja que se guarda en el arqueo.

    Args:
        caja: Caja que se cierra.

    Returns:
        dict: Claves `caja_id`, `caja_nombre` y `sucursal_nombre`.
    """
    sucursal = getattr(caja, _config('ARQUEO_CAMPO_SUCURSAL'), None)
    return {
        'caja_id': str(caja.pk),
        'caja_nombre': str(caja),
        'sucursal_nombre': str(sucursal) if sucursal is not None else '',
    }


def bloquear_caja(caja):
    """Cambia el estado de la caja al estado de bloqueo configurado.

    Args:
        caja: Caja que se cierra.
    """
    campo = _config('ARQUEO_CAMPO_ESTADO')
    setattr(caja, campo, _config('ARQUEO_ESTADO_BLOQUEADA'))
    caja.save(update_fields=[campo])
