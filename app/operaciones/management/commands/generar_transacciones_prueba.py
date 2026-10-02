"""Comando para generar transacciones de prueba del historial (solo desarrollo).

Uso (desde la raíz del repositorio):
    docker compose exec web python manage.py generar_transacciones_prueba <username>
    docker compose exec web python manage.py generar_transacciones_prueba <username> --cantidad 50 --semilla 1

El usuario debe tener al menos un `Cliente` asociado (por ejemplo, mediante
"Convertirse en cliente" o "Asignar cliente"); las transacciones se reparten
entre sus clientes y quedan registradas como operadas por ese usuario. Si
faltan monedas, medios de pago del usuario o cajeros, se crean datos de prueba.
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from clientes.models import Cliente
from mpagos.models import MedioPago
from operaciones.models import Moneda, TasaDeCambio, Transaccion

# Monedas de prueba: código -> (nombre, tasa base en PYG)
MONEDAS_PRUEBA = {
    'USD': ('Dólar Estadounidense', Decimal('7500')),
    'EUR': ('Euro', Decimal('8200')),
    'BRL': ('Real Brasileño', Decimal('1400')),
}

# Margen usado cuando la moneda no tiene una TasaDeCambio cargada
MARGEN_POR_DEFECTO = Decimal('0.02')

CAJEROS_PRUEBA = [
    ('cajero_demo1', 'María', 'González'),
    ('cajero_demo2', 'Carlos', 'Benítez'),
]

# Pesos para que la mayoría de las transacciones de prueba estén confirmadas
PESOS_ESTADO = {
    Transaccion.Estado.CONFIRMADA: 7,
    Transaccion.Estado.PENDIENTE: 2,
    Transaccion.Estado.CANCELADA: 1,
}


class Command(BaseCommand):
    """Genera transacciones aleatorias operadas por un usuario en nombre de sus clientes."""

    help = "Genera transacciones de prueba para el historial de un usuario (solo con DEBUG=True)."

    def add_arguments(self, parser):
        """Define los argumentos del comando.

        Args:
            parser: Parser de argumentos de Django.
        """
        parser.add_argument('username', help="Usuario que opera; las transacciones se reparten entre sus clientes.")
        parser.add_argument('--cantidad', type=int, default=30, help="Cantidad de transacciones (por defecto 30).")
        parser.add_argument('--semilla', type=int, default=None, help="Semilla aleatoria para resultados repetibles.")

    def handle(self, *args, **options):
        """Crea las transacciones de prueba.

        Raises:
            CommandError: Si `DEBUG` está desactivado, el usuario no existe,
                no tiene clientes asociados o la cantidad no es positiva.
        """
        if not settings.DEBUG:
            raise CommandError("Este comando solo puede ejecutarse con DEBUG=True.")
        if options['cantidad'] < 1:
            raise CommandError("La cantidad debe ser mayor que cero.")

        Usuario = get_user_model()
        try:
            usuario = Usuario.objects.get(username=options['username'])
        except Usuario.DoesNotExist:
            raise CommandError(f"No existe el usuario '{options['username']}'.")

        clientes = list(Cliente.objects.filter(usuarios_asociados__usuario=usuario))
        if not clientes:
            raise CommandError(
                f"El usuario '{usuario.username}' no tiene clientes asociados. "
                "Asocie uno con 'Convertirse en cliente' o 'Asignar cliente'."
            )

        rng = random.Random(options['semilla'])
        monedas = self._obtener_monedas()
        medios = self._obtener_medios_pago(usuario)
        cajeros = self._obtener_cajeros()
        ahora = timezone.now()

        for _ in range(options['cantidad']):
            moneda = rng.choice(monedas)
            tipo = rng.choice(Transaccion.Tipo.values)
            estado = rng.choices(list(PESOS_ESTADO), weights=list(PESOS_ESTADO.values()))[0]
            tasa = self._tasa_para(moneda, tipo)
            monto_divisa = Decimal(rng.randrange(10, 2000))
            monto_pyg = (monto_divisa * tasa).quantize(Decimal('0.01'))

            # Compra: el cliente paga PYG y recibe la divisa. Venta: al revés.
            if tipo == Transaccion.Tipo.COMPRA:
                monto_pagado, monto_recibido = monto_pyg, monto_divisa
            else:
                monto_pagado, monto_recibido = monto_divisa, monto_pyg

            fecha = (ahora - timedelta(days=rng.randint(0, 90))).replace(
                hour=rng.randint(8, 19), minute=rng.randint(0, 59), second=0, microsecond=0
            )

            Transaccion.objects.create(
                cliente=rng.choice(clientes),
                usuario=usuario,
                cajero=None if estado == Transaccion.Estado.PENDIENTE else rng.choice(cajeros),
                tipo=tipo,
                moneda=moneda,
                medio_pago=rng.choice(medios),
                monto_pagado=monto_pagado,
                monto_recibido=monto_recibido,
                tasa_aplicada=tasa,
                facturada=estado == Transaccion.Estado.CONFIRMADA and rng.random() < 0.6,
                dispositivo=rng.choice(Transaccion.Dispositivo.values),
                estado=estado,
                fecha=min(fecha, ahora),
            )

        self.stdout.write(self.style.SUCCESS(
            f"Se generaron {options['cantidad']} transacciones de prueba para '{usuario.username}'."
        ))

    def _obtener_monedas(self):
        """Devuelve las monedas habilitadas, creando las de prueba si no hay ninguna."""
        monedas = list(Moneda.objects.filter(habilitada=True))
        if monedas:
            return monedas
        return [
            Moneda.objects.get_or_create(codigo=codigo, defaults={'nombre': nombre})[0]
            for codigo, (nombre, _) in MONEDAS_PRUEBA.items()
        ]

    def _obtener_medios_pago(self, usuario):
        """Devuelve los medios de pago activos del usuario, creando dos si no tiene."""
        medios = list(MedioPago.objects.filter(usuario=usuario, activo=True))
        if medios:
            return medios
        nombre = usuario.get_full_name() or usuario.username
        return [
            MedioPago.objects.create(
                usuario=usuario, tipo='TARJETA', nombre_titular=nombre,
                banco_emisor='Banco de Prueba', numero_enmascarado='**** 4321', es_predeterminado=True,
            ),
            MedioPago.objects.create(
                usuario=usuario, tipo='SIPAP', nombre_titular=nombre,
                banco_emisor='Banco de Prueba', numero_enmascarado='**** 8765',
            ),
        ]

    def _obtener_cajeros(self):
        """Devuelve los usuarios con rol `Cajero`, creando dos de prueba si no hay."""
        Usuario = get_user_model()
        cajeros = list(Usuario.objects.filter(roles__contains=['Cajero']))
        if cajeros:
            return cajeros
        creados = []
        for username, nombre, apellido in CAJEROS_PRUEBA:
            cajero, creado = Usuario.objects.get_or_create(
                username=username,
                defaults={'first_name': nombre, 'last_name': apellido, 'roles': ['Cajero']},
            )
            if creado:
                cajero.set_unusable_password()
                cajero.save()
            creados.append(cajero)
        return creados

    def _tasa_para(self, moneda, tipo):
        """Calcula el precio en PYG aplicado a la operación.

        Cuando el cliente compra, la casa vende (precio de venta); cuando el
        cliente vende, la casa compra (precio de compra). Si la tasa cargada
        da un precio no positivo (margen mayor que la base), se usa el valor
        de prueba para no generar montos negativos.

        Args:
            moneda: Moneda operada.
            tipo: Valor de `Transaccion.Tipo`.

        Returns:
            Decimal: Precio de una unidad de la divisa en PYG.
        """
        tasa = TasaDeCambio.objects.filter(moneda=moneda).first()
        if tasa:
            precio = tasa.calcular_precio_venta() if tipo == Transaccion.Tipo.COMPRA else tasa.calcular_precio_compra()
            if precio > 0:
                return precio
        base = MONEDAS_PRUEBA.get(moneda.codigo, ('', Decimal('1000')))[1]
        factor = 1 + MARGEN_POR_DEFECTO if tipo == Transaccion.Tipo.COMPRA else 1 - MARGEN_POR_DEFECTO
        return (base * factor).quantize(Decimal('0.0001'))
