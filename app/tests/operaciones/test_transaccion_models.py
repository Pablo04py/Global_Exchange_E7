"""
Pruebas unitarias del modelo Transaccion (historial de transacciones, SCRUM-19).

Evalúa la representación textual, el orden por defecto, las monedas pagada y
recibida según el tipo de operación y la protección de los registros de auditoría.
"""

from decimal import Decimal
from unittest.mock import patch

from django.db.models import ProtectedError
from django.test import TestCase

from operaciones.models import Transaccion, ConfiguracionComision, TasaDeCambio
from clientes.models import Cliente
from .datos_historial import HistorialDatosMixin, fecha_local


class TransaccionModelTestCase(HistorialDatosMixin, TestCase):
    """Pruebas del modelo Transaccion."""

    def setUp(self):
        super().setUp()
        
        # Configurar campos obligatorios
        ConfiguracionComision.objects.get_or_create(
            categoria=Cliente.Categoria.MINORISTA,
            defaults={'porcentaje': Decimal('2.00')}
        )
        self.tasa_usd, _ = TasaDeCambio.objects.get_or_create(
            moneda=self.usd,
            defaults={
                'tasa_base': Decimal('7500.00'),
                'margen_compra': Decimal('50.00'),
                'margen_venta': Decimal('50.00')
            }
        )

        # Interceptamos Transaccion.objects.create
        self.original_create = Transaccion.objects.create

        def custom_create(**kwargs):
            cliente = kwargs.get('cliente') or self.cliente_a
            categoria = getattr(cliente, 'categoria', Cliente.Categoria.MINORISTA)
            tasa = kwargs.get('tasa_referencia') or self.tasa_usd

            kwargs.setdefault('categoria_cliente_aplicada', categoria)
            kwargs.setdefault('porcentaje_comision', Decimal('2.00'))
            kwargs.setdefault('monto_comision', Decimal('15000.00'))
            kwargs.setdefault('moneda_comision', 'PYG')
            kwargs.setdefault('tasa_referencia', tasa)

            return self.original_create(**kwargs)

        self.patcher = patch.object(Transaccion.objects, 'create', side_effect=custom_create)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        super().tearDown()

    def test_str_incluye_tipo_moneda_cliente_y_fecha(self):
        """Verifica el formato `TIPO MONEDA - cliente (dd/mm/aaaa hh:mm)`."""
        t = self.crear_transaccion(fecha=fecha_local(2026, 9, 15, 14, 30))
        self.assertEqual(str(t), "Compra USD - Ana Pérez (15/09/2026 14:30)")

    def test_ordering_mas_reciente_primero(self):
        """Verifica que por defecto se ordene de la más reciente a la más antigua."""
        antigua = self.crear_transaccion(fecha=fecha_local(2026, 1, 1))
        reciente = self.crear_transaccion(fecha=fecha_local(2026, 9, 1))
        self.assertEqual(list(Transaccion.objects.all()), [reciente, antigua])

    def test_monedas_en_compra(self):
        """En una compra el cliente paga PYG y recibe la divisa."""
        t = self.crear_transaccion(tipo=Transaccion.Tipo.COMPRA)
        self.assertEqual(t.moneda_pagada, 'PYG')
        self.assertEqual(t.moneda_recibida, 'USD')

    def test_monedas_en_venta(self):
        """En una venta el cliente paga la divisa y recibe PYG."""
        t = self.crear_transaccion(tipo=Transaccion.Tipo.VENTA)
        self.assertEqual(t.moneda_pagada, 'USD')
        self.assertEqual(t.moneda_recibida, 'PYG')

    def test_valores_por_defecto(self):
        """Verifica los valores por defecto de estado, dispositivo y facturación."""
        t = Transaccion.objects.create(
            cliente=self.cliente_a, usuario=self.usuario_a, tipo=Transaccion.Tipo.VENTA,
            moneda=self.usd, medio_pago=self.tarjeta_a,
            monto_pagado=10, monto_recibido=74000, tasa_aplicada=7400,
        )
        self.assertEqual(t.estado, Transaccion.Estado.PENDIENTE)
        self.assertEqual(t.dispositivo, Transaccion.Dispositivo.OTRO)
        self.assertFalse(t.facturada)
        self.assertIsNone(t.cajero)
        self.assertIsNotNone(t.fecha)

    def test_no_se_puede_borrar_cliente_con_transacciones(self):
        """Verifica que PROTECT impida perder el historial al borrar el cliente."""
        self.crear_transaccion()
        with self.assertRaises(ProtectedError):
            self.cliente_a.delete()

    def test_no_se_puede_borrar_usuario_que_opero(self):
        """Verifica que PROTECT impida perder el registro de quién operó al borrar el usuario."""
        self.crear_transaccion()
        with self.assertRaises(ProtectedError):
            self.usuario_a.delete()

    def test_borrar_cajero_conserva_transaccion(self):
        """Verifica que al borrar el cajero la transacción se conserve sin cajero."""
        t = self.crear_transaccion()
        self.cajero.delete()
        t.refresh_from_db()
        self.assertIsNone(t.cajero)