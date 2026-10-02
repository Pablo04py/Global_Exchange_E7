"""
Pruebas de los filtros y la paginación del historial de transacciones (SCRUM-19).

Evalúa cada filtro de FiltroHistorialForm a través de la vista, la validación
de rangos y la paginación de 20 registros que conserva los filtros aplicados.
"""

from decimal import Decimal
from unittest.mock import patch

from django.core.paginator import Paginator
from django.test import TestCase
from django.urls import reverse

from clientes.models import Cliente
from operaciones.models import Transaccion, TasaDeCambio, ConfiguracionComision
from operaciones.views import TRANSACCIONES_POR_PAGINA
from .datos_historial import HistorialDatosMixin, Usuario, fecha_local

URL = reverse('historial_transacciones')


class BaseHistorialTestCase(HistorialDatosMixin, TestCase):
    """Base con setUp extendido para inyectar comisiones y tasa de referencia por defecto."""

    def setUp(self):
        super().setUp()

        # Configuración de comisiones para evitar errores de restricción NOT NULL
        ConfiguracionComision.objects.get_or_create(
            categoria=Cliente.Categoria.MINORISTA,
            defaults={'porcentaje': Decimal('2.00')}
        )
        ConfiguracionComision.objects.get_or_create(
            categoria=Cliente.Categoria.VIP,
            defaults={'porcentaje': Decimal('1.00')}
        )

        # Crear tasa de cambio de referencia si no existe
        self.tasa_usd, _ = TasaDeCambio.objects.get_or_create(
            moneda=self.usd,
            defaults={
                'tasa_base': Decimal('7500.00'),
                'margen_compra': Decimal('50.00'),
                'margen_venta': Decimal('50.00')
            }
        )

        # Interceptamos la creación de Transacciones
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


class HistorialFiltrosTestCase(BaseHistorialTestCase):
    """Pruebas de cada filtro del historial."""

    def setUp(self):
        """Crea dos transacciones del cliente A que difieren en todos los campos filtrables."""
        super().setUp()
        self.cajero2 = Usuario.objects.create_user(username='cajero2', first_name='Carlos', last_name='Benítez')
        self.t1 = self.crear_transaccion(
            tipo=Transaccion.Tipo.COMPRA, moneda=self.usd, medio_pago=self.tarjeta_a,
            monto_pagado=Decimal('765000'), monto_recibido=Decimal('100'), facturada=True,
            dispositivo=Transaccion.Dispositivo.IPHONE, cajero=self.cajero,
            estado=Transaccion.Estado.CONFIRMADA, fecha=fecha_local(2026, 9, 1, 9, 0),
        )
        self.t2 = self.crear_transaccion(
            tipo=Transaccion.Tipo.VENTA, moneda=self.eur,
            medio_pago=self.sipap_a, monto_pagado=Decimal('50'), monto_recibido=Decimal('400000'),
            facturada=False, dispositivo=Transaccion.Dispositivo.WINDOWS, cajero=self.cajero2,
            estado=Transaccion.Estado.CANCELADA, fecha=fecha_local(2026, 9, 20, 17, 45),
        )
        self.client.force_login(self.usuario_a)

    def _resultado(self, **filtros):
        """Devuelve la lista de transacciones mostradas para los filtros dados."""
        return list(self.client.get(URL, filtros).context['page_obj'])

    def test_sin_filtros_muestra_todas(self):
        """Sin filtros se listan todas las transacciones del cliente activo (y ninguna de otro cliente)."""
        self.crear_transaccion(cliente=self.cliente_b)
        self.assertEqual(self._resultado(), [self.t2, self.t1])

    def test_filtro_fecha_desde_y_hasta(self):
        """Filtra por rango de fechas (inclusivo)."""
        self.assertEqual(self._resultado(fecha_desde='2026-09-10'), [self.t2])
        self.assertEqual(self._resultado(fecha_hasta='2026-09-01'), [self.t1])
        self.assertEqual(self._resultado(fecha_desde='2026-09-01', fecha_hasta='2026-09-20'), [self.t2, self.t1])

    def test_filtro_hora_desde_y_hasta(self):
        """Filtra por franja horaria, independiente de la fecha."""
        self.assertEqual(self._resultado(hora_desde='12:00'), [self.t2])
        self.assertEqual(self._resultado(hora_hasta='12:00'), [self.t1])
        self.assertEqual(self._resultado(hora_desde='08:00', hora_hasta='10:00'), [self.t1])

    def test_filtro_fecha_y_hora_combinados(self):
        """Fecha y hora se combinan: septiembre por la tarde."""
        self.assertEqual(
            self._resultado(fecha_desde='2026-09-01', fecha_hasta='2026-09-30', hora_desde='15:00'), [self.t2]
        )

    def test_filtro_tipo(self):
        """Filtra por compra o venta."""
        self.assertEqual(self._resultado(tipo='COMPRA'), [self.t1])
        self.assertEqual(self._resultado(tipo='VENTA'), [self.t2])

    def test_filtro_moneda(self):
        """Filtra por moneda."""
        self.assertEqual(self._resultado(moneda=str(self.eur.id)), [self.t2])

    def test_filtro_medio_pago(self):
        """Filtra por medio de pago."""
        self.assertEqual(self._resultado(medio_pago=self.tarjeta_a.pk), [self.t1])

    def test_filtro_monto_pagado(self):
        """Filtra por rango de monto pagado."""
        self.assertEqual(self._resultado(monto_pagado_min='1000'), [self.t1])
        self.assertEqual(self._resultado(monto_pagado_max='1000'), [self.t2])

    def test_filtro_monto_recibido(self):
        """Filtra por rango de monto recibido."""
        self.assertEqual(self._resultado(monto_recibido_min='1000'), [self.t2])
        self.assertEqual(self._resultado(monto_recibido_min='50', monto_recibido_max='150'), [self.t1])

    def test_filtro_facturada(self):
        """Filtra por transacciones facturadas o no facturadas."""
        self.assertEqual(self._resultado(facturada='si'), [self.t1])
        self.assertEqual(self._resultado(facturada='no'), [self.t2])

    def test_filtro_dispositivo(self):
        """Filtra por dispositivo."""
        self.assertEqual(self._resultado(dispositivo='IPHONE'), [self.t1])

    def test_filtro_cajero(self):
        """Filtra por el cajero que atendió la operación."""
        self.assertEqual(self._resultado(cajero=self.cajero2.pk), [self.t2])

    def test_filtro_estado(self):
        """Filtra por estado de la transacción."""
        self.assertEqual(self._resultado(estado='CONFIRMADA'), [self.t1])
        self.assertEqual(self._resultado(estado='PENDIENTE'), [])

    def test_filtros_combinados(self):
        """Varios filtros se aplican a la vez (AND)."""
        self.assertEqual(self._resultado(tipo='COMPRA', moneda=str(self.eur.id)), [])
        self.assertEqual(self._resultado(tipo='VENTA', moneda=str(self.eur.id), facturada='no'), [self.t2])

    def test_opcion_cajero_muestra_nombre_completo(self):
        """El filtro de cajero muestra el nombre completo de cada cajero."""
        response = self.client.get(URL)
        self.assertContains(response, 'Carlos Benítez')

    def test_sin_resultados_muestra_mensaje(self):
        """Si ningún registro coincide se muestra el mensaje de filtros sin resultados."""
        response = self.client.get(URL, {'estado': 'PENDIENTE'})
        self.assertContains(response, 'No hay transacciones que coincidan con los filtros')

    def test_rango_invalido_muestra_error_e_ignora_el_campo(self):
        """Un rango con 'desde' mayor que 'hasta' muestra un error y no filtra por ese campo."""
        response = self.client.get(URL, {'fecha_desde': '2026-09-30', 'fecha_hasta': '2026-09-01'})
        self.assertIn('fecha_hasta', response.context['form'].errors)
        self.assertEqual(response.context['total'], 2)

    def test_valor_invalido_no_rompe_la_vista(self):
        """Un valor mal formado (ej. monto no numérico) responde 200 con error de validación."""
        response = self.client.get(URL, {'monto_pagado_min': 'abc'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('monto_pagado_min', response.context['form'].errors)


class HistorialPaginacionTestCase(BaseHistorialTestCase):
    """Pruebas de la paginación del historial."""

    def setUp(self):
        """Crea 25 transacciones del cliente A (5 de ellas ventas)."""
        super().setUp()
        for dia in range(1, 26):
            tipo = Transaccion.Tipo.VENTA if dia <= 5 else Transaccion.Tipo.COMPRA
            self.crear_transaccion(tipo=tipo, fecha=fecha_local(2026, 8, dia))
        self.client.force_login(self.usuario_a)

    def test_primera_pagina_tiene_20(self):
        """La primera página muestra 20 transacciones."""
        response = self.client.get(URL)
        self.assertEqual(TRANSACCIONES_POR_PAGINA, 20)
        self.assertEqual(len(response.context['page_obj']), 20)
        self.assertEqual(response.context['total'], 25)

    def test_segunda_pagina_tiene_el_resto(self):
        """La segunda página muestra las 5 restantes (las más antiguas)."""
        page_obj = self.client.get(URL, {'page': 2}).context['page_obj']
        self.assertEqual(len(page_obj), 5)
        self.assertEqual(page_obj[0].fecha, fecha_local(2026, 8, 5))

    def test_pagina_fuera_de_rango_o_invalida(self):
        """Una página inexistente o no numérica no produce error."""
        self.assertEqual(self.client.get(URL, {'page': 99}).context['page_obj'].number, 2)
        self.assertEqual(self.client.get(URL, {'page': 'abc'}).context['page_obj'].number, 1)

    def test_numeros_de_pagina_y_pagina_actual_marcada(self):
        """Se muestran los números de página como enlaces y la actual queda marcada."""
        response = self.client.get(URL, {'page': 2})
        self.assertContains(response, '<span class="ht-page ht-page-actual" aria-current="page">2</span>', html=True)
        self.assertContains(response, '<a class="ht-page" href="?page=1">1</a>', html=True)
        self.assertEqual(list(response.context['rango_paginas']), [1, 2])

    def test_flechas_deshabilitadas_en_los_extremos(self):
        """En la primera página las flechas hacia atrás no son enlaces (y en la última, las de adelante)."""
        primera = self.client.get(URL).content.decode()
        self.assertNotIn('title="Primera página"', primera)
        self.assertIn('title="Última página"', primera)
        ultima = self.client.get(URL, {'page': 2}).content.decode()
        self.assertIn('title="Primera página"', ultima)
        self.assertNotIn('title="Última página"', ultima)

    def test_muchas_paginas_se_abrevian(self):
        """Con muchas páginas se muestran extremos y vecinas de la actual, abreviando el resto."""
        base = Transaccion.objects.first()
        Transaccion.objects.bulk_create([  # 25 + 375 = 400 transacciones -> 20 páginas
            Transaccion(
                cliente=self.cliente_a, usuario=self.usuario_a, cajero=self.cajero, tipo=base.tipo, moneda=self.usd,
                medio_pago=self.tarjeta_a, monto_pagado=base.monto_pagado, monto_recibido=base.monto_recibido,
                tasa_aplicada=base.tasa_aplicada, fecha=fecha_local(2026, 1, 1 + i % 28),
                categoria_cliente_aplicada=self.cliente_a.categoria,
                porcentaje_comision=Decimal('2.00'),
                monto_comision=Decimal('15000.00'),
                moneda_comision='PYG',
                tasa_referencia=self.tasa_usd,
            )
            for i in range(375)
        ])
        rango = self.client.get(URL, {'page': 10}).context['rango_paginas']
        elipsis = Paginator.ELLIPSIS
        self.assertEqual(rango, [1, elipsis, 8, 9, 10, 11, 12, elipsis, 20])

    def test_enlaces_de_paginacion_conservan_filtros(self):
        """Los enlaces de página mantienen los filtros aplicados en la URL."""
        for dia in range(1, 21):
            self.crear_transaccion(tipo=Transaccion.Tipo.VENTA, fecha=fecha_local(2026, 7, dia))
        response = self.client.get(URL, {'tipo': 'VENTA'})
        self.assertEqual(response.context['total'], 25)
        self.assertContains(response, '?tipo=VENTA&amp;page=2')