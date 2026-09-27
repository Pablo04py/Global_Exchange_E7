"""Datos de prueba compartidos por los tests del historial de transacciones."""

from datetime import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from clientes.models import Cliente, UsuarioCliente
from mpagos.models import MedioPago
from operaciones.models import Moneda, Transaccion

Usuario = get_user_model()


def fecha_local(anio, mes, dia, hora=10, minuto=0):
    """Crea un datetime consciente de zona horaria en la hora local (America/Asuncion)."""
    return timezone.make_aware(datetime(anio, mes, dia, hora, minuto))


class HistorialDatosMixin:
    """Crea dos usuarios registrados como clientes, monedas, medios de pago y un cajero.

    - `usuario_a`, registrado como cliente mediante `cliente_a` (minorista).
    - `usuario_b`, registrado como cliente mediante `cliente_b` (VIP); sus
      transacciones no deben verse desde `usuario_a`.
    """

    def setUp(self):
        """Carga los datos base comunes."""
        self.usuario_a = Usuario.objects.create_user(username='cliente_a', password='password123')
        self.usuario_b = Usuario.objects.create_user(username='cliente_b', password='password123')
        self.cajero = Usuario.objects.create_user(
            username='cajero1', password='password123', first_name='María', last_name='González', roles=['Cajero']
        )

        self.cliente_a = Cliente.objects.create(
            tipo_persona=Cliente.TipoPersona.FISICA, nombre_o_denominacion='Ana Pérez',
            documento='1111111', categoria=Cliente.Categoria.MINORISTA,
        )
        self.cliente_b = Cliente.objects.create(
            tipo_persona=Cliente.TipoPersona.JURIDICA, nombre_o_denominacion='Empresa B S.A.',
            documento='80000000-1', categoria=Cliente.Categoria.VIP,
        )
        UsuarioCliente.objects.create(usuario=self.usuario_a, cliente=self.cliente_a)
        UsuarioCliente.objects.create(usuario=self.usuario_b, cliente=self.cliente_b)

        self.usd = Moneda.objects.create(codigo='USD', nombre='Dólar')
        self.eur = Moneda.objects.create(codigo='EUR', nombre='Euro')

        self.tarjeta_a = MedioPago.objects.create(
            usuario=self.usuario_a, tipo='TARJETA', nombre_titular='Ana Pérez', numero_enmascarado='**** 1234'
        )
        self.sipap_a = MedioPago.objects.create(
            usuario=self.usuario_a, tipo='SIPAP', nombre_titular='Ana Pérez', numero_enmascarado='**** 5678'
        )
        self.tarjeta_b = MedioPago.objects.create(
            usuario=self.usuario_b, tipo='TARJETA', nombre_titular='Empresa B', numero_enmascarado='**** 9999'
        )

    def crear_transaccion(self, usuario=None, **campos):
        """Crea una transacción; por defecto una compra confirmada de 100 USD de `usuario_a`.

        Args:
            usuario: Usuario (cliente) dueño de la transacción (por defecto `usuario_a`).
            **campos: Campos de `Transaccion` que reemplazan a los valores por defecto.

        Returns:
            Transaccion: La transacción creada.
        """
        usuario = usuario or self.usuario_a
        es_a = usuario == self.usuario_a
        valores = {
            'usuario': usuario,
            'cajero': self.cajero,
            'tipo': Transaccion.Tipo.COMPRA,
            'moneda': self.usd,
            'medio_pago': self.tarjeta_a if es_a else self.tarjeta_b,
            'monto_pagado': Decimal('765000.00'),
            'monto_recibido': Decimal('100.00'),
            'tasa_aplicada': Decimal('7650.0000'),
            'facturada': False,
            'dispositivo': Transaccion.Dispositivo.WINDOWS,
            'estado': Transaccion.Estado.CONFIRMADA,
            'fecha': fecha_local(2026, 9, 15),
        }
        valores.update(campos)
        return Transaccion.objects.create(**valores)
