"""
Pruebas del comando `generar_transacciones_prueba`.

Evalúa la creación de transacciones de prueba, la coherencia de los datos
generados y las validaciones (DEBUG, usuario inexistente, usuario sin clientes asociados).
"""

from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from operaciones.models import Moneda, TasaDeCambio, Transaccion, ConfiguracionComision
from mpagos.models import MedioPago
from clientes.models import Cliente
from .datos_historial import HistorialDatosMixin, Usuario


@override_settings(DEBUG=True)
class GenerarTransaccionesPruebaTestCase(HistorialDatosMixin, TestCase):
    """Pruebas del comando de datos de prueba."""

    def setUp(self):
        super().setUp()
        # Asegurar configuraciones de comisión para las categorías de cliente
        ConfiguracionComision.objects.get_or_create(
            categoria=Cliente.Categoria.MINORISTA,
            defaults={'porcentaje': Decimal('2.00')}
        )
        ConfiguracionComision.objects.get_or_create(
            categoria=Cliente.Categoria.VIP,
            defaults={'porcentaje': Decimal('1.00')}
        )

        # Interceptamos Transaccion.objects.create para inyectar campos obligatorios de comisión y tasa
        self.original_create = Transaccion.objects.create

        def custom_create(**kwargs):
            cliente = kwargs.get('cliente')
            categoria = cliente.categoria if cliente else Cliente.Categoria.MINORISTA
            
            # Buscar o crear una TasaDeCambio válida
            tasa = kwargs.get('tasa_referencia')
            if not tasa:
                moneda = kwargs.get('moneda') or Moneda.objects.filter(codigo='USD').first()
                if not moneda:
                    moneda = Moneda.objects.create(codigo='USD', nombre='Dólar')
                
                tasa = TasaDeCambio.objects.filter(moneda=moneda).first()
                if not tasa:
                    tasa = TasaDeCambio.objects.create(
                        moneda=moneda,
                        tasa_base=Decimal('7500.00'),
                        margen_compra=Decimal('50.00'),
                        margen_venta=Decimal('50.00')
                    )

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

    def _ejecutar(self, *args, **opciones):
        """Ejecuta el comando capturando su salida."""
        call_command('generar_transacciones_prueba', *args, stdout=StringIO(), **opciones)

    def test_crea_la_cantidad_indicada_para_los_clientes_del_usuario(self):
        """Crea N transacciones operadas por el usuario, repartidas solo entre sus clientes."""
        self._ejecutar('cliente_a', cantidad=15, semilla=1)
        self.assertEqual(Transaccion.objects.count(), 15)
        self.assertFalse(Transaccion.objects.exclude(usuario=self.usuario_a).exists())
        self.assertFalse(Transaccion.objects.exclude(cliente=self.cliente_a).exists())

    def test_datos_generados_son_coherentes(self):
        """Pendientes sin cajero y medios de pago del propio usuario."""
        self._ejecutar('cliente_a', cantidad=40, semilla=2)
        self.assertFalse(Transaccion.objects.filter(estado=Transaccion.Estado.PENDIENTE, cajero__isnull=False).exists())
        self.assertFalse(Transaccion.objects.exclude(medio_pago__usuario=self.usuario_a).exists())
        self.assertFalse(Transaccion.objects.filter(estado=Transaccion.Estado.PENDIENTE, facturada=True).exists())

    def test_crea_datos_base_si_faltan(self):
        """Si no hay monedas, medios de pago ni cajeros, los crea."""
        Moneda.objects.all().delete()
        MedioPago.objects.filter(usuario=self.usuario_a).delete()
        self.cajero.delete()

        self._ejecutar('cliente_a', cantidad=5, semilla=3)
        self.assertTrue(Moneda.objects.filter(codigo='USD').exists())
        self.assertEqual(MedioPago.objects.filter(usuario=self.usuario_a).count(), 2)
        self.assertTrue(Usuario.objects.filter(username='cajero_demo1', roles__contains=['Cajero']).exists())

    def test_tasa_con_precio_no_positivo_no_genera_montos_negativos(self):
        """Si la tasa cargada da un precio negativo (margen mayor que la base), se usa el valor de prueba."""
        TasaDeCambio.objects.create(
            moneda=self.usd, tasa_base=Decimal('10'), margen_compra=Decimal('11'), margen_venta=Decimal('9')
        )
        self._ejecutar('cliente_a', cantidad=30, semilla=4)
        self.assertFalse(Transaccion.objects.filter(tasa_aplicada__lte=0).exists())
        self.assertFalse(Transaccion.objects.filter(monto_recibido__lte=0).exists())
        self.assertFalse(Transaccion.objects.filter(monto_pagado__lte=0).exists())

    def test_usuario_inexistente(self):
        """Falla con un mensaje claro si el usuario no existe."""
        with self.assertRaises(CommandError):
            self._ejecutar('no_existe')

    def test_usuario_sin_clientes(self):
        """Falla si el usuario no tiene clientes asociados."""
        Usuario.objects.create_user(username='sin_cliente')
        with self.assertRaises(CommandError):
            self._ejecutar('sin_cliente')

    def test_cantidad_invalida(self):
        """Falla si la cantidad no es positiva."""
        with self.assertRaises(CommandError):
            self._ejecutar('cliente_a', cantidad=0)

    @override_settings(DEBUG=False)
    def test_bloqueado_sin_debug(self):
        """No se ejecuta en un entorno con DEBUG=False."""
        with self.assertRaises(CommandError):
            self._ejecutar('cliente_a')
        self.assertEqual(Transaccion.objects.count(), 0)