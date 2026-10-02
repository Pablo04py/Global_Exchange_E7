from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from clientes.models import Cliente
from operaciones.models import (
    Moneda, 
    TasaDeCambio, 
    Transaccion, 
    LogTransaccion, 
    ConfiguracionComision
)
from mpagos.models import MedioPago
from operaciones.services import cambiar_estado_transaccion

User = get_user_model()


class EstadoYInmutabilidadTestCase(TestCase):
    def setUp(self):
        # 1. Crear Usuario
        self.usuario = User.objects.create_user(
            username="testuser", password="password123"
        )

        # 2. Crear Cliente
        self.cliente = Cliente.objects.create(
            categoria=Cliente.Categoria.MINORISTA
        )

        # 3. Configurar Comisión inicial
        ConfiguracionComision.objects.get_or_create(
            categoria=Cliente.Categoria.MINORISTA,
            defaults={'porcentaje': Decimal("2.00")}
        )

        # 4. Moneda y Tasa de Cambio
        self.moneda = Moneda.objects.create(codigo="USD", nombre="Dólar")
        self.tasa = TasaDeCambio.objects.create(
            moneda=self.moneda,
            tasa_base=Decimal("7500.00"),
            margen_compra=Decimal("50.00"),
            margen_venta=Decimal("50.00")
        )

        # 5. Medio de Pago (incluyendo usuario obligatorio)
        self.medio_pago = MedioPago.objects.create(
            cliente=self.cliente,
            usuario=self.usuario,
            tipo='TARJETA',
            nombre_titular='Titular Prueba',
            banco_emisor='Banco Prueba',
            numero_enmascarado='**** **** **** 1234',
            activo=True
        )

        # 6. Transacción inicial en estado PENDIENTE
        self.transaccion = Transaccion.objects.create(
            cliente=self.cliente,
            usuario=self.usuario,
            tipo=Transaccion.Tipo.COMPRA,
            moneda=self.moneda,
            medio_pago=self.medio_pago,
            monto_pagado=Decimal("100.00"),
            monto_recibido=Decimal("745000.00"),
            tasa_referencia=self.tasa,
            tasa_aplicada=Decimal("7550.00"),
            categoria_cliente_aplicada=self.cliente.categoria,
            porcentaje_comision=Decimal("2.00"),
            monto_comision=Decimal("15000.00"),
            moneda_comision="PYG",
            estado=Transaccion.Estado.PENDIENTE
        )

    def test_cambiar_estado_a_cancelada_exitoso_y_crea_log(self):
        """Prueba que pasa de PENDIENTE a CANCELADA y registra el Log (RNF15)."""
        motivo = "Cancelado por el cliente antes del pago"
        
        transaccion_actualizada = cambiar_estado_transaccion(
            transaccion=self.transaccion,
            nuevo_estado=Transaccion.Estado.CANCELADA,
            usuario=self.usuario,
            motivo=motivo
        )

        # Verificar estado
        self.assertEqual(transaccion_actualizada.estado, Transaccion.Estado.CANCELADA)

        # Verificar auditoría inmutable (RNF15)
        log = LogTransaccion.objects.filter(transaccion=self.transaccion).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.estado_anterior, Transaccion.Estado.PENDIENTE)
        self.assertEqual(log.estado_nuevo, Transaccion.Estado.CANCELADA)
        self.assertEqual(log.usuario, self.usuario)
        self.assertEqual(log.motivo, motivo)

    def test_no_permite_transicion_invalidas(self):
        """Prueba que no permite saltar a estados no válidos según las reglas."""
        with self.assertRaises(ValidationError):
            cambiar_estado_transaccion(
                transaccion=self.transaccion,
                nuevo_estado="ESTADO_INVALIDO",
                usuario=self.usuario
            )

    def test_estado_cancelada_es_terminal(self):
        """Prueba que una vez CANCELADA no se puede reabrir ni modificar (Inmutabilidad)."""
        # Cambiar a estado terminal
        cambiar_estado_transaccion(
            transaccion=self.transaccion,
            nuevo_estado=Transaccion.Estado.CANCELADA,
            usuario=self.usuario
        )

        # Intentar reabrir a PENDIENTE -> Debe fallar
        with self.assertRaises(ValidationError):
            cambiar_estado_transaccion(
                transaccion=self.transaccion,
                nuevo_estado=Transaccion.Estado.PENDIENTE,
                usuario=self.usuario,
                motivo="Intento de reabrir operación"
            )