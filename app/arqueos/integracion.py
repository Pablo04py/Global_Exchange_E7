"""Punto de conexión del arqueo con el módulo de caja de otras historias.

El cierre de caja (SCRUM-40) necesita datos que implementan otras historias:

- SCRUM-36 (asignación, app `caja`): `SesionCaja` es el turno de un cajero en
  una `Caja`; tiene `cajero`, `estado` (`ASIGNADA`, `ABIERTA`, `EN_ARQUEO`,
  `CERRADA`) y `fecha_cierre`. `Caja` tiene `estado` (`DISPONIBLE`, `EN_USO`,
  `INACTIVA`, `MANTENIMIENTO`).
- SCRUM-37 (apertura): pone el turno en `ABIERTA`.
- SCRUM-39 (operación de cajeros): los movimientos de efectivo del turno.
  El saldo registrado se calcula en `arqueos.saldos.saldo_registrado`.

Este módulo concentra esa dependencia. Al cerrar, el turno pasa a `CERRADA`
(con su fecha de cierre) y la caja a `INACTIVA`, que es el bloqueo. El
Administrador General la habilita nuevamente (vuelve a `DISPONIBLE`) desde la
pantalla de cajas bloqueadas.

Los nombres se leen de `settings` (con los valores por defecto de abajo), así
que si las otras historias cambian algún nombre se ajusta la configuración sin
tocar la lógica del arqueo:

| Setting                         | Por defecto                        | Significado                                   |
|---------------------------------|------------------------------------|-----------------------------------------------|
| `ARQUEO_MODELO_TURNO`           | `'caja.SesionCaja'`                | Modelo del turno, como `app.Modelo`           |
| `ARQUEO_CAMPO_CAJERO`           | `'cajero'`                         | Campo del turno con el cajero                 |
| `ARQUEO_CAMPO_ESTADO`           | `'estado'`                         | Campo del turno con su estado                 |
| `ARQUEO_ESTADO_ABIERTA`         | `'ABIERTA'`                        | Estado de un turno abierto                    |
| `ARQUEO_ESTADO_TURNO_CERRADO`   | `'CERRADA'`                        | Estado que se asigna al turno al cerrar       |
| `ARQUEO_CAMPO_FECHA_CIERRE`     | `'fecha_cierre'`                   | Campo del turno con la fecha de cierre        |
| `ARQUEO_CAMPO_CAJA`             | `'caja'`                           | Relación del turno con su caja                |
| `ARQUEO_CAMPO_ESTADO_CAJA`      | `'estado'`                         | Campo de la caja con su estado                |
| `ARQUEO_ESTADO_CAJA_BLOQUEADA`  | `'INACTIVA'`                       | Estado que se asigna a la caja al cerrar      |
| `ARQUEO_ESTADO_CAJA_HABILITADA` | `'DISPONIBLE'`                     | Estado que se asigna a la caja al habilitarla |
| `ARQUEO_CAMPO_SUCURSAL`         | `'sucursal'`                       | Campo de la caja con su sucursal (si existe)  |
| `ARQUEO_FUNCION_SALDO`          | `'arqueos.saldos.saldo_registrado'`| Función `f(turno) -> {codigo_moneda: monto}`  |

Mientras alguna pieza no exista, las funciones lanzan `ModuloCajaNoDisponible`
y la vista de cierre muestra un aviso en lugar de fallar.
"""

from decimal import Decimal

from django.apps import apps
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, FieldError
from django.utils import timezone
from django.utils.module_loading import import_string

CONFIGURACION_POR_DEFECTO = {
    'ARQUEO_MODELO_TURNO': 'caja.SesionCaja',
    'ARQUEO_CAMPO_CAJERO': 'cajero',
    'ARQUEO_CAMPO_ESTADO': 'estado',
    'ARQUEO_ESTADO_ABIERTA': 'ABIERTA',
    'ARQUEO_ESTADO_TURNO_CERRADO': 'CERRADA',
    'ARQUEO_CAMPO_FECHA_CIERRE': 'fecha_cierre',
    'ARQUEO_CAMPO_CAJA': 'caja',
    'ARQUEO_CAMPO_ESTADO_CAJA': 'estado',
    'ARQUEO_ESTADO_CAJA_BLOQUEADA': 'INACTIVA',
    'ARQUEO_ESTADO_CAJA_HABILITADA': 'DISPONIBLE',
    'ARQUEO_CAMPO_SUCURSAL': 'sucursal',
    'ARQUEO_FUNCION_SALDO': 'arqueos.saldos.saldo_registrado',
}


class ModuloCajaNoDisponible(Exception):
    """El modelo de turno o la función de saldo registrado aún no existen o están mal configurados."""


def _config(nombre):
    """Devuelve el valor de un setting de integración o su valor por defecto.

    Args:
        nombre: Nombre del setting (ver `CONFIGURACION_POR_DEFECTO`).

    Returns:
        str: Valor configurado.
    """
    return getattr(settings, nombre, CONFIGURACION_POR_DEFECTO[nombre])


def modelo_turno():
    """Devuelve el modelo de turno de caja configurado.

    Returns:
        type[Model]: Clase del modelo (por defecto `caja.SesionCaja`).

    Raises:
        ModuloCajaNoDisponible: Si el modelo no existe.
    """
    try:
        return apps.get_model(_config('ARQUEO_MODELO_TURNO'))
    except (LookupError, ValueError) as error:
        raise ModuloCajaNoDisponible(
            f"El modelo de turno de caja '{_config('ARQUEO_MODELO_TURNO')}' no está disponible."
        ) from error


def obtener_turno_abierto(cajero, bloquear_fila=False):
    """Devuelve el turno abierto del cajero (su caja asignada y abierta).

    Args:
        cajero: Usuario con rol Cajero.
        bloquear_fila: Si es `True`, bloquea la fila (`SELECT ... FOR UPDATE`)
            para evitar dos cierres simultáneos; usar dentro de una transacción.

    Returns:
        Model | None: El turno abierto, o `None` si el cajero no tiene ninguno.

    Raises:
        ModuloCajaNoDisponible: Si el modelo o sus campos no están disponibles.
    """
    Turno = modelo_turno()
    filtros = {
        _config('ARQUEO_CAMPO_CAJERO'): cajero,
        _config('ARQUEO_CAMPO_ESTADO'): _config('ARQUEO_ESTADO_ABIERTA'),
    }
    consulta = Turno.objects.select_related(_config('ARQUEO_CAMPO_CAJA'))
    if bloquear_fila:
        consulta = consulta.select_for_update()
    try:
        return consulta.filter(**filtros).first()
    except FieldError as error:  # nombre de campo mal configurado
        raise ModuloCajaNoDisponible(f"No se pudo consultar el turno de caja: {error}") from error


def _caja_de(turno):
    """Devuelve la caja del turno."""
    return getattr(turno, _config('ARQUEO_CAMPO_CAJA'))


def obtener_saldo_registrado(turno):
    """Devuelve el saldo registrado (esperado) del turno por moneda.

    Args:
        turno: Turno abierto.

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
    return {str(moneda).upper(): Decimal(str(monto)) for moneda, monto in funcion(turno).items()}


def datos_de_caja(turno):
    """Toma la "foto" de la caja del turno que se guarda en el arqueo.

    Args:
        turno: Turno que se cierra.

    Returns:
        dict: Claves `caja_id`, `caja_nombre` y `sucursal_nombre` (vacía si la
        caja todavía no tiene sucursal).
    """
    caja = _caja_de(turno)
    sucursal = getattr(caja, _config('ARQUEO_CAMPO_SUCURSAL'), None)
    return {
        'caja_id': str(caja.pk),
        'caja_nombre': str(caja),
        'sucursal_nombre': str(sucursal) if sucursal is not None else '',
    }


def cerrar_turno_y_bloquear_caja(turno):
    """Marca el turno como cerrado (con su fecha) y bloquea la caja.

    Args:
        turno: Turno que se cierra.
    """
    campo_estado = _config('ARQUEO_CAMPO_ESTADO')
    campo_fecha = _config('ARQUEO_CAMPO_FECHA_CIERRE')
    setattr(turno, campo_estado, _config('ARQUEO_ESTADO_TURNO_CERRADO'))
    setattr(turno, campo_fecha, timezone.now())
    turno.save(update_fields=[campo_estado, campo_fecha])

    caja = _caja_de(turno)
    campo_estado_caja = _config('ARQUEO_CAMPO_ESTADO_CAJA')
    setattr(caja, campo_estado_caja, _config('ARQUEO_ESTADO_CAJA_BLOQUEADA'))
    caja.save(update_fields=[campo_estado_caja])


def modelo_caja():
    """Devuelve el modelo de caja (el destino de la relación del turno con su caja).

    Returns:
        type[Model]: Clase del modelo (por defecto `caja.Caja`).

    Raises:
        ModuloCajaNoDisponible: Si el modelo de turno o su relación no existen.
    """
    try:
        return modelo_turno()._meta.get_field(_config('ARQUEO_CAMPO_CAJA')).related_model
    except FieldDoesNotExist as error:
        raise ModuloCajaNoDisponible(f"No se pudo obtener el modelo de caja: {error}") from error


def cajas_bloqueadas():
    """Devuelve las cajas que están en el estado de bloqueo configurado.

    Returns:
        QuerySet: Cajas en estado bloqueado (por defecto `INACTIVA`).
    """
    return modelo_caja().objects.filter(
        **{_config('ARQUEO_CAMPO_ESTADO_CAJA'): _config('ARQUEO_ESTADO_CAJA_BLOQUEADA')}
    )


def habilitar_caja(caja):
    """Cambia el estado de la caja al estado habilitado configurado.

    Args:
        caja: Caja bloqueada.
    """
    campo = _config('ARQUEO_CAMPO_ESTADO_CAJA')
    setattr(caja, campo, _config('ARQUEO_ESTADO_CAJA_HABILITADA'))
    caja.save(update_fields=[campo])
