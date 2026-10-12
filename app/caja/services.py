
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone


from operaciones.models import Moneda

from .models import (
    Caja, EstadoCaja, EstadoSesionCaja, MovimientoCaja,
    SentidoMovimiento, SesionCaja, TipoMovimiento,
)

MONEDA_LOCAL = 'PYG'
CERO = Decimal('0')
ESTADOS_ACTIVOS = [EstadoSesionCaja.ASIGNADA, EstadoSesionCaja.ABIERTA]


def nombre_usuario(user):
    """Los usuarios de Keycloak tienen un hash como username: mostramos nombre o email."""
    return user.get_full_name() or user.email or user.username




def saldo_por_moneda(sesion):
    """Devuelve {'PYG': Decimal, 'USD': Decimal, ...} con el efectivo actual de la sesión."""
    filas = sesion.movimientos.values('moneda').annotate(
        entradas=Sum('monto', filter=Q(sentido=SentidoMovimiento.ENTRADA)),
        salidas=Sum('monto', filter=Q(sentido=SentidoMovimiento.SALIDA)),
    )
    return {f['moneda']: (f['entradas'] or CERO) - (f['salidas'] or CERO) for f in filas}


def resumen_por_moneda(sesion):
    """Resumen de la sesión por moneda, listo para mostrar.

    Devuelve una lista (PYG primero) con un dict por moneda habilitada:
    {'moneda', 'apertura', 'entradas', 'salidas', 'saldo'}.
    - apertura: lo que se contó al abrir la caja.
    - entradas: lo recibido de clientes durante la sesión.
    - salidas: lo entregado a clientes durante la sesión.
    """
    es_entrada = Q(sentido=SentidoMovimiento.ENTRADA)
    es_apertura = Q(tipo=TipoMovimiento.APERTURA)
    filas = sesion.movimientos.values('moneda').annotate(
        apertura=Sum('monto', filter=es_entrada & es_apertura),
        entradas=Sum('monto', filter=es_entrada & ~es_apertura),
        salidas=Sum('monto', filter=Q(sentido=SentidoMovimiento.SALIDA)),
    )
    por_moneda = {f['moneda']: f for f in filas}

    codigos = set(por_moneda) | set(
        Moneda.objects.filter(habilitada=True).values_list('codigo', flat=True)
    )
    resumen = []
    for codigo in sorted(codigos, key=lambda c: (c != MONEDA_LOCAL, c)):
        f = por_moneda.get(codigo, {})
        apertura = f.get('apertura') or CERO
        entradas = f.get('entradas') or CERO
        salidas = f.get('salidas') or CERO
        resumen.append({
            'moneda': codigo,
            'apertura': apertura,
            'entradas': entradas,
            'salidas': salidas,
            'saldo': apertura + entradas - salidas,
        })
    return resumen


@transaction.atomic
def registrar_apertura(sesion, montos):
    """Crea un movimiento APERTURA/ENTRADA por cada moneda con monto > 0.

    Args:
        sesion: SesionCaja que se está abriendo.
        montos: dict {'PYG': Decimal, 'USD': Decimal, ...}.

    Es idempotente: si la sesión ya tiene movimientos de apertura, no duplica.
    """
    if sesion.movimientos.filter(tipo=TipoMovimiento.APERTURA).exists():
        return []

    creados = []
    for moneda, monto in montos.items():
        if monto is None or Decimal(monto) <= 0:
            continue
        creados.append(MovimientoCaja.objects.create(
            sesion=sesion, tipo=TipoMovimiento.APERTURA,
            sentido=SentidoMovimiento.ENTRADA, moneda=moneda, monto=monto,
            justificacion="Fondo inicial de apertura",
        ))
    return creados


@transaction.atomic
def asignar_cajero(caja, cajero, asignado_por):
    """SCRUM-36: asigna una caja disponible a un cajero (con lock para evitar doble asignación)."""
    caja = Caja.objects.select_for_update().get(pk=caja.pk)

    if not caja.activa or caja.estado != EstadoCaja.DISPONIBLE:
        raise ValidationError("La caja seleccionada no está disponible.")
    if SesionCaja.objects.filter(caja=caja, estado__in=ESTADOS_ACTIVOS).exists():
        raise ValidationError("Esta caja ya está asignada a otro cajero.")
    if SesionCaja.objects.filter(cajero=cajero, estado__in=ESTADOS_ACTIVOS).exists():
        raise ValidationError("Este cajero ya tiene una caja asignada o abierta actualmente.")

    sesion = SesionCaja.objects.create(
        caja=caja, cajero=cajero, asignado_por=asignado_por,
        estado=EstadoSesionCaja.ASIGNADA,
    )
    return sesion


@transaction.atomic
def apertura_caja(cajero, montos):
    """SCRUM-37: abre la sesión asignada al cajero.

    `montos` es {'PYG': Decimal, 'USD': Decimal, ...}. Crea un movimiento
    APERTURA/ENTRADA por cada moneda con monto mayor a cero.
    """
    sesion = (
        SesionCaja.objects.select_for_update()
        .filter(cajero=cajero, estado=EstadoSesionCaja.ASIGNADA)
        .first()
    )
    if not sesion:
        raise ValidationError("No tienes ninguna caja asignada pendiente de apertura.")

    caja = Caja.objects.select_for_update().get(pk=sesion.caja_id)

    for moneda, monto in montos.items():
        if monto and monto > 0:
            MovimientoCaja.objects.create(
                sesion=sesion, moneda=moneda, monto=monto,
                sentido=SentidoMovimiento.ENTRADA, tipo=TipoMovimiento.APERTURA,
                justificacion=f"Fondo inicial de apertura en {moneda}",
            )

    # Compatibilidad con la info visual de la sesión (solo guaraníes)
    sesion.monto_inicial = montos.get(MONEDA_LOCAL, CERO)
    sesion.estado = EstadoSesionCaja.ABIERTA
    sesion.fecha_apertura = timezone.now()
    sesion.save()

    caja.estado = EstadoCaja.EN_USO
    caja.save()
    sesion.caja = caja
    return sesion


@transaction.atomic
def registrar_movimiento_transaccion(sesion, transaccion):
    """Registra en la caja el efectivo que entra y sale por una transacción.

    - La divisa extranjera siempre es billete físico: entra o sale de la caja.
    - El guaraní solo mueve la caja si el medio de pago es EFECTIVO. Con tarjeta
      o transferencia el dinero no pasa por el cajón.
    - Es idempotente: si la transacción ya tiene movimientos, no duplica.
    - Lanza ValidationError si no hay stock suficiente de lo que se entrega.
    - Bloquea la sesión durante la operación para que dos operaciones
      simultáneas no gasten el mismo stock.
    """
    sesion = SesionCaja.objects.select_for_update().get(pk=sesion.pk)

    if sesion.estado != EstadoSesionCaja.ABIERTA:
        raise ValidationError("La sesión de caja no está abierta.")

    existentes = list(sesion.movimientos.filter(transaccion=transaccion))
    if existentes:
        return existentes

    en_efectivo = transaccion.medio_pago.tipo == 'EFECTIVO'
    patas = [
        (SentidoMovimiento.ENTRADA, transaccion.moneda_pagada, transaccion.monto_pagado),
        (SentidoMovimiento.SALIDA, transaccion.moneda_recibida, transaccion.monto_recibido),
    ]

    creados = []
    for sentido, moneda, monto in patas:
        if moneda == MONEDA_LOCAL and not en_efectivo:
            continue  # el guaraní viajó por tarjeta/transferencia, no por el cajón

        if sentido == SentidoMovimiento.SALIDA:
            disponible = saldo_por_moneda(sesion).get(moneda, CERO)
            if disponible < monto:
                raise ValidationError(
                    f"Stock insuficiente de {moneda} en caja: hay {disponible} y se necesitan {monto}."
                )

        creados.append(MovimientoCaja.objects.create(
            sesion=sesion, transaccion=transaccion, tipo=TipoMovimiento.OPERACION,
            sentido=sentido, moneda=moneda, monto=monto,
            justificacion=f"Operación {transaccion.pk}",
        ))
    return creados


@transaction.atomic
def transferir_entre_cajas(origen, destino, moneda, monto, justificacion=''):
    """RF33: SALIDA en la caja origen y ENTRADA en la destino, ambas tipo TRANSFERENCIA."""
    moneda = moneda.upper()
    monto = Decimal(monto)

    if origen.pk == destino.pk:
        raise ValidationError("La caja de origen y la de destino deben ser distintas.")
    if monto <= CERO:
        raise ValidationError("El monto a transferir debe ser mayor a cero.")

    # Se bloquean ambas sesiones en orden fijo para evitar interbloqueos.
    bloqueadas = {
        s.pk: s for s in
        SesionCaja.objects.select_for_update().filter(pk__in=[origen.pk, destino.pk]).order_by('pk')
    }
    origen, destino = bloqueadas[origen.pk], bloqueadas[destino.pk]

    for s in (origen, destino):
        if s.estado != EstadoSesionCaja.ABIERTA:
            raise ValidationError(f"La sesión de la caja {s.caja.codigo} no está abierta.")

    disponible = saldo_por_moneda(origen).get(moneda, CERO)
    if disponible < monto:
        raise ValidationError(
            f"Stock insuficiente de {moneda} en la caja de origen: hay {disponible} y se necesitan {monto}."
        )

    texto = justificacion or "Transferencia entre cajas"
    salida = MovimientoCaja.objects.create(
        sesion=origen, tipo=TipoMovimiento.TRANSFERENCIA, sentido=SentidoMovimiento.SALIDA,
        moneda=moneda, monto=monto,
        justificacion=f"{texto} - hacia {destino.caja.codigo}"[:255],
    )
    entrada = MovimientoCaja.objects.create(
        sesion=destino, tipo=TipoMovimiento.TRANSFERENCIA, sentido=SentidoMovimiento.ENTRADA,
        moneda=moneda, monto=monto,
        justificacion=f"{texto} - desde {origen.caja.codigo}"[:255],
    )
    return salida, entrada
