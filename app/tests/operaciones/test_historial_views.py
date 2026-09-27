"""
Pruebas de integración de la vista del historial de transacciones (SCRUM-19).

Evalúa el control de acceso (solo clientes registrados), el aislamiento entre
usuarios, la naturaleza de solo lectura de la vista y el contenido del listado.
"""

import re

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from clientes.models import Cliente, UsuarioCliente
from operaciones.models import Transaccion
from .datos_historial import HistorialDatosMixin, Usuario, fecha_local

URL = reverse('historial_transacciones')


class HistorialAccesoTestCase(HistorialDatosMixin, TestCase):
    """Pruebas de acceso y seguridad del historial."""

    def test_usuario_anonimo_redirige_al_login(self):
        """Un visitante no autenticado es redirigido al login (HTTP 302)."""
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(reverse('convertirse_en_cliente'), response.url)

    def test_usuario_sin_cliente_redirige_a_convertirse_en_cliente(self):
        """Un usuario autenticado sin cliente asociado no accede al historial."""
        sin_cliente = Usuario.objects.create_user(username='sin_cliente', password='password123')
        self.client.force_login(sin_cliente)
        response = self.client.get(URL)
        self.assertRedirects(response, reverse('convertirse_en_cliente'), fetch_redirect_response=False)

    def test_clientes_de_todas_las_categorias_acceden(self):
        """Clientes minoristas, corporativos y VIP pueden ver su historial."""
        for i, categoria in enumerate(Cliente.Categoria.values):
            usuario = Usuario.objects.create_user(username=f'cat_{categoria}', password='password123')
            cliente = Cliente.objects.create(
                tipo_persona=Cliente.TipoPersona.FISICA, nombre_o_denominacion=f'Cliente {categoria}',
                documento=f'doc-{i}', categoria=categoria,
            )
            UsuarioCliente.objects.create(usuario=usuario, cliente=cliente)
            self.client.force_login(usuario)
            with self.subTest(categoria=categoria):
                self.assertEqual(self.client.get(URL).status_code, 200)

    def test_usuario_no_ve_transacciones_de_otro_usuario(self):
        """El usuario A solo ve sus transacciones, nunca las del usuario B."""
        propia = self.crear_transaccion(usuario=self.usuario_a)
        self.crear_transaccion(usuario=self.usuario_b)
        self.client.force_login(self.usuario_a)

        response = self.client.get(URL)
        self.assertEqual(list(response.context['page_obj']), [propia])
        self.assertNotContains(response, '**** 9999')

    def test_forzar_medio_de_pago_ajeno_en_url_no_expone_datos(self):
        """Enviar el id de un medio de pago ajeno no muestra transacciones ajenas."""
        self.crear_transaccion(usuario=self.usuario_a)
        ajena = self.crear_transaccion(usuario=self.usuario_b)
        self.client.force_login(self.usuario_a)

        response = self.client.get(URL, {'medio_pago': self.tarjeta_b.pk})
        self.assertIn('medio_pago', response.context['form'].errors)
        self.assertNotIn(ajena, list(response.context['page_obj']))

    def test_forzar_cajero_ajeno_en_url_no_expone_datos(self):
        """Enviar el id de un cajero que solo atendió al usuario B no muestra sus transacciones."""
        cajero_b = Usuario.objects.create_user(username='cajero_b', roles=['Cajero'])
        self.crear_transaccion(usuario=self.usuario_a)
        ajena = self.crear_transaccion(usuario=self.usuario_b, cajero=cajero_b)
        self.client.force_login(self.usuario_a)

        response = self.client.get(URL, {'cajero': cajero_b.pk})
        self.assertIn('cajero', response.context['form'].errors)
        self.assertNotIn(ajena, list(response.context['page_obj']))

    def test_opciones_de_filtro_solo_incluyen_datos_propios(self):
        """Las listas de medios de pago, monedas y cajeros del filtro no incluyen datos del usuario B."""
        cajero_b = Usuario.objects.create_user(username='cajero_b', roles=['Cajero'])
        self.crear_transaccion(usuario=self.usuario_a)
        self.crear_transaccion(usuario=self.usuario_b, moneda=self.eur, cajero=cajero_b)
        self.client.force_login(self.usuario_a)

        form = self.client.get(URL).context['form']
        self.assertNotIn('cliente', form.fields)
        self.assertEqual(list(form.fields['medio_pago'].queryset), [self.tarjeta_a])
        self.assertEqual(list(form.fields['moneda'].queryset), [self.usd])
        self.assertEqual(list(form.fields['cajero'].queryset), [self.cajero])


class HistorialSoloLecturaTestCase(HistorialDatosMixin, TestCase):
    """Pruebas que garantizan que el historial sea solo de consulta."""

    def setUp(self):
        """Autentica al usuario A con una transacción."""
        super().setUp()
        self.transaccion = self.crear_transaccion()
        self.client.force_login(self.usuario_a)

    def test_post_no_permitido(self):
        """Un POST responde 405 y no crea transacciones."""
        response = self.client.post(URL, {'tipo': 'VENTA'})
        self.assertEqual(response.status_code, 405)
        self.assertEqual(Transaccion.objects.count(), 1)

    def test_put_y_delete_no_permitidos(self):
        """PUT y DELETE responden 405 y no alteran los datos."""
        self.assertEqual(self.client.put(URL).status_code, 405)
        self.assertEqual(self.client.delete(URL).status_code, 405)
        self.assertTrue(Transaccion.objects.filter(pk=self.transaccion.pk).exists())

    def test_pantalla_sin_acciones_de_edicion(self):
        """La página no ofrece formularios POST (salvo el logout del layout) ni acciones de editar o eliminar."""
        response = self.client.get(URL)
        acciones_post = re.findall(r'<form[^>]*method="post"[^>]*action="([^"]*)"', response.content.decode())
        self.assertEqual(acciones_post, [reverse('oidc_logout')])
        self.assertNotContains(response, 'Editar')
        self.assertNotContains(response, 'Eliminar')


class HistorialListadoTestCase(HistorialDatosMixin, TestCase):
    """Pruebas del contenido y orden del listado."""

    def test_cliente_sin_transacciones(self):
        """Un cliente sin operaciones ve el listado vacío y el mensaje correspondiente."""
        self.client.force_login(self.usuario_a)
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'operaciones/historial.html')
        self.assertEqual(response.context['total'], 0)
        self.assertContains(response, 'Todavía no realizaste transacciones')

    def test_orden_mas_reciente_primero(self):
        """Las transacciones se listan de la más reciente a la más antigua."""
        antigua = self.crear_transaccion(fecha=fecha_local(2026, 7, 1))
        reciente = self.crear_transaccion(fecha=fecha_local(2026, 9, 20))
        media = self.crear_transaccion(fecha=fecha_local(2026, 8, 10))
        self.client.force_login(self.usuario_a)

        response = self.client.get(URL)
        self.assertEqual(list(response.context['page_obj']), [reciente, media, antigua])

    def test_muestra_los_datos_de_la_transaccion(self):
        """Se muestran fecha, hora, tipo, medio de pago, montos, cajero, estado, factura y dispositivo.

        Los montos usan el formato regional (locale `es`: miles con espacio duro y coma decimal).
        """
        self.crear_transaccion(
            fecha=fecha_local(2026, 9, 15, 14, 30), facturada=True, dispositivo=Transaccion.Dispositivo.IPHONE
        )
        self.client.force_login(self.usuario_a)
        response = self.client.get(URL)

        for texto in ['15/09/2026', '14:30', 'Compra USD', '**** 1234', '765\xa0000,00', 'PYG',
                      '100,00', 'María González', 'Confirmada', 'iPhone']:
            with self.subTest(texto=texto):
                self.assertContains(response, texto)

    def test_transaccion_pendiente_sin_cajero(self):
        """Una transacción pendiente se muestra sin cajero asignado."""
        self.crear_transaccion(estado=Transaccion.Estado.PENDIENTE, cajero=None)
        self.client.force_login(self.usuario_a)
        response = self.client.get(URL)
        self.assertContains(response, 'Pendiente')
        self.assertNotContains(response, 'María González')

    def test_no_muestra_columna_ni_filtro_de_cliente(self):
        """El cliente es el propio usuario: no hay columna ni filtro "Cliente"."""
        self.crear_transaccion()
        self.client.force_login(self.usuario_a)
        response = self.client.get(URL)
        self.assertNotContains(response, '<th>Cliente</th>', html=False)
        self.assertNotContains(response, 'name="cliente"', html=False)

    def test_pagina_incluye_menu_lateral(self):
        """El historial se muestra con el menú lateral según el rol del usuario."""
        self.client.force_login(self.usuario_a)
        self.assertTrue(self.client.get(URL).context['menu_sections'])

    def test_menu_con_rol_enlaza_al_historial_real(self):
        """En el menú de un usuario con rol, el enlace del historial apunta a la vista real."""
        self.usuario_a.groups.add(Group.objects.create(name='Cajero'))
        self.client.force_login(self.usuario_a)
        response = self.client.get(reverse('dashboard'))
        urls = [item['url'] for seccion in response.context['menu_sections'] for item in seccion['items']]
        self.assertIn(URL, urls)
        self.assertNotIn('/historial/', urls)
