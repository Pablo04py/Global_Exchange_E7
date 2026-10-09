"""
Pruebas de los reportes de auditoría de caja (SCRUM-41).

Evalúa el acceso (solo Administrador General), los filtros por fecha,
sucursal, cajero y nivel de discrepancia, el resumen, la exportación a CSV y
que el reporte sea de solo lectura e imprimible.
"""

import re
from datetime import datetime
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from arqueos.models import ArqueoCaja, DetalleArqueo
from .apoyo import Usuario

URL = reverse('reporte_arqueos')
URL_CSV = reverse('exportar_reporte_arqueos')


def fecha_local(anio, mes, dia, hora=18, minuto=0):
    """Crea un datetime consciente de zona horaria en la hora local (America/Asuncion)."""
    return timezone.make_aware(datetime(anio, mes, dia, hora, minuto))


def crear_arqueo(cajero, sucursal, fecha, saldos, caja='Caja 1'):
    """Crea un arqueo con un detalle por moneda.

    Args:
        cajero: Usuario que cerró.
        sucursal: Nombre de la sucursal.
        fecha: Fecha y hora del cierre.
        saldos: `{moneda: (registrado, declarado)}`.
        caja: Nombre de la caja.

    Returns:
        ArqueoCaja: El arqueo creado.
    """
    arqueo = ArqueoCaja.objects.create(
        caja_id=caja, caja_nombre=caja, sucursal_nombre=sucursal, cajero=cajero, fecha_cierre=fecha
    )
    for moneda, (registrado, declarado) in saldos.items():
        diferencia = Decimal(declarado) - Decimal(registrado)
        resultado = ('SOBRANTE' if diferencia > 0 else 'FALTANTE' if diferencia < 0 else 'CUADRA')
        DetalleArqueo.objects.create(
            arqueo=arqueo, moneda=moneda, saldo_registrado=registrado, saldo_declarado=declarado,
            diferencia=diferencia, resultado=resultado,
        )
    return arqueo


class ReporteBaseTestCase(TestCase):
    """Crea usuarios y cuatro arqueos con distintos niveles de discrepancia."""

    def setUp(self):
        """Carga administrador, cajeros y arqueos de dos sucursales."""
        self.admin = Usuario.objects.create_user(username='admin1', roles=['Administrador General'])
        self.maria = Usuario.objects.create_user(
            username='cajero1', first_name='María', last_name='González', roles=['Cajero']
        )
        self.carlos = Usuario.objects.create_user(
            username='cajero2', first_name='Carlos', last_name='Benítez', roles=['Cajero']
        )
        self.cuadra = crear_arqueo(self.maria, 'Casa Central', fecha_local(2026, 10, 1),
                                   {'PYG': ('1000000', '1000000'), 'USD': ('500', '500')})
        self.faltante = crear_arqueo(self.maria, 'Casa Central', fecha_local(2026, 10, 5),
                                     {'PYG': ('2000000', '2000000'), 'USD': ('900', '880')})
        self.sobrante = crear_arqueo(self.carlos, 'Sucursal Norte', fecha_local(2026, 10, 7),
                                     {'PYG': ('500000', '550000')}, caja='Caja 2')
        self.mixto = crear_arqueo(self.carlos, 'Sucursal Norte', fecha_local(2026, 10, 9),
                                  {'PYG': ('100', '150'), 'USD': ('10', '5')}, caja='Caja 2')
        self.client.force_login(self.admin)

    def _arqueos(self, **filtros):
        """Devuelve los arqueos que muestra el reporte con los filtros dados."""
        return list(self.client.get(URL, filtros).context['arqueos'])


class ReporteAccesoTestCase(ReporteBaseTestCase):
    """Pruebas de acceso y solo lectura."""

    def test_administrador_accede(self):
        """El Administrador General ve el reporte."""
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'arqueos/reporte.html')

    def test_cajero_y_anonimo_no_acceden(self):
        """Un cajero recibe 403 en el reporte y en la exportación; un anónimo también."""
        self.client.force_login(self.maria)
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.assertEqual(self.client.get(URL_CSV).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(URL).status_code, 403)

    def test_solo_lectura(self):
        """El reporte solo acepta GET y no ofrece formularios POST (salvo el logout del layout)."""
        self.assertEqual(self.client.post(URL).status_code, 405)
        self.assertEqual(self.client.post(URL_CSV).status_code, 405)
        acciones_post = re.findall(r'<form[^>]*method="post"[^>]*action="([^"]*)"',
                                   self.client.get(URL).content.decode())
        self.assertEqual(acciones_post, [reverse('oidc_logout')])

    def test_imprimible(self):
        """La página ofrece el botón de imprimir y estilos de impresión."""
        response = self.client.get(URL)
        self.assertContains(response, 'window.print()')
        self.assertContains(response, '@media print')


class ReporteContenidoTestCase(ReporteBaseTestCase):
    """Pruebas del listado y el resumen."""

    def test_lista_todos_del_mas_reciente_al_mas_antiguo(self):
        """Sin filtros aparecen todos los cierres, del más reciente al más antiguo."""
        self.assertEqual(self._arqueos(), [self.mixto, self.sobrante, self.faltante, self.cuadra])

    def test_resumen(self):
        """El resumen cuenta cierres por nivel; un cierre mixto cuenta como sobrante y faltante."""
        resumen = self.client.get(URL).context['resumen']
        self.assertEqual(resumen, {'total': 4, 'con_faltante': 2, 'con_sobrante': 2, 'sin_discrepancia': 1})

    def test_muestra_saldos_y_resultados(self):
        """La tabla muestra sucursal, cajero, saldos, diferencia y resultado."""
        response = self.client.get(URL)
        for texto in ['Casa Central', 'Sucursal Norte', 'María González', 'Carlos Benítez',
                      '900,00', '880,00', '-20,00', 'Faltante', 'Sobrante', 'Cuadra']:
            with self.subTest(texto=texto):
                self.assertContains(response, texto)

    def test_sin_cierres(self):
        """Sin arqueos registrados se muestra el aviso correspondiente."""
        ArqueoCaja.objects.all().delete()
        self.assertContains(self.client.get(URL), 'Todavía no hay cierres de caja registrados')


class ReporteFiltrosTestCase(ReporteBaseTestCase):
    """Pruebas de cada filtro."""

    def test_filtro_fechas(self):
        """Filtra por rango de fechas de cierre (inclusivo)."""
        self.assertEqual(self._arqueos(fecha_desde='2026-10-05'), [self.mixto, self.sobrante, self.faltante])
        self.assertEqual(self._arqueos(fecha_hasta='2026-10-05'), [self.faltante, self.cuadra])
        self.assertEqual(self._arqueos(fecha_desde='2026-10-05', fecha_hasta='2026-10-07'),
                         [self.sobrante, self.faltante])

    def test_rango_de_fechas_invalido(self):
        """Un rango invertido muestra error y no filtra por fecha."""
        response = self.client.get(URL, {'fecha_desde': '2026-10-09', 'fecha_hasta': '2026-10-01'})
        self.assertIn('fecha_hasta', response.context['form'].errors)
        self.assertEqual(len(response.context['arqueos']), 4)

    def test_filtro_sucursal(self):
        """Filtra por sucursal; las opciones salen de los arqueos registrados."""
        self.assertEqual(self._arqueos(sucursal='Casa Central'), [self.faltante, self.cuadra])
        opciones = [valor for valor, _ in self.client.get(URL).context['form'].fields['sucursal'].choices]
        self.assertEqual(opciones, ['', 'Casa Central', 'Sucursal Norte'])

    def test_sucursal_inexistente(self):
        """Una sucursal que no está en las opciones da error y no se filtra por ella."""
        response = self.client.get(URL, {'sucursal': 'Inventada'})
        self.assertIn('sucursal', response.context['form'].errors)
        self.assertEqual(len(response.context['arqueos']), 4)

    def test_filtro_cajero(self):
        """Filtra por cajero; las opciones son solo cajeros con arqueos."""
        self.assertEqual(self._arqueos(cajero=self.carlos.pk), [self.mixto, self.sobrante])
        opciones = list(self.client.get(URL).context['form'].fields['cajero'].queryset)
        self.assertCountEqual(opciones, [self.maria, self.carlos])

    def test_filtro_nivel(self):
        """Filtra por nivel; un cierre con sobrante y faltante aparece en ambos niveles."""
        self.assertEqual(self._arqueos(nivel='SIN'), [self.cuadra])
        self.assertEqual(self._arqueos(nivel='SOBRANTE'), [self.mixto, self.sobrante])
        self.assertEqual(self._arqueos(nivel='FALTANTE'), [self.mixto, self.faltante])

    def test_filtros_combinados_y_resumen_filtrado(self):
        """Los filtros se combinan y el resumen refleja solo los cierres filtrados."""
        response = self.client.get(URL, {'sucursal': 'Sucursal Norte', 'nivel': 'FALTANTE'})
        self.assertEqual(list(response.context['arqueos']), [self.mixto])
        self.assertEqual(response.context['resumen']['total'], 1)

    def test_sin_resultados_con_filtros(self):
        """Si ningún cierre coincide se muestra el aviso de filtros."""
        response = self.client.get(URL, {'cajero': self.maria.pk, 'nivel': 'SOBRANTE'})
        self.assertContains(response, 'No hay cierres que coincidan con los filtros')


class ReporteCsvTestCase(ReporteBaseTestCase):
    """Pruebas de la exportación a CSV."""

    def _csv(self, **filtros):
        """Descarga el CSV y devuelve la respuesta y sus líneas (sin BOM)."""
        response = self.client.get(URL_CSV, filtros)
        texto = response.content.decode('utf-8')
        return response, texto, texto.lstrip('﻿').splitlines()

    def test_descarga_csv(self):
        """Devuelve un adjunto CSV en UTF-8 con BOM para Excel."""
        response, texto, _ = self._csv()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('attachment; filename="reporte_arqueos_', response['Content-Disposition'])
        self.assertTrue(texto.startswith('﻿'))

    def test_una_fila_por_moneda_con_formato_de_excel(self):
        """Encabezado y una fila por moneda, con `;`, coma decimal y hora local."""
        _, _, lineas = self._csv(cajero=self.maria.pk)
        self.assertEqual(lineas[0], 'Fecha de cierre;Sucursal;Caja;Cajero;Moneda;'
                                    'Saldo registrado;Saldo declarado;Diferencia;Resultado')
        self.assertEqual(len(lineas), 1 + 4)  # 2 arqueos x 2 monedas
        self.assertIn('05/10/2026 18:00;Casa Central;Caja 1;María González;USD;900,00;880,00;-20,00;Faltante',
                      lineas)

    def test_csv_respeta_los_filtros(self):
        """La exportación aplica los mismos filtros que la pantalla."""
        _, _, lineas = self._csv(nivel='SIN')
        self.assertEqual(len(lineas), 1 + 2)  # solo el arqueo que cuadra (PYG y USD)
        self.assertTrue(all('Cuadra' in linea for linea in lineas[1:]))

    def test_boton_exportar_conserva_filtros(self):
        """El enlace de exportación de la pantalla incluye los filtros aplicados."""
        response = self.client.get(URL, {'nivel': 'FALTANTE'})
        self.assertContains(response, f'{URL_CSV}?nivel=FALTANTE')
