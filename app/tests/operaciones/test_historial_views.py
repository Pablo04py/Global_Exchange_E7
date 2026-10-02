"""
Pruebas de integración de la vista del historial de transacciones (SCRUM-19).

Evalúa el control de acceso (solo usuarios con clientes asociados), el uso del
cliente activo de la sesión, el aislamiento entre clientes, la naturaleza de
solo lectura de la vista y el contenido del listado.
"""

import re
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from clientes.models import Cliente, UsuarioCliente
from operaciones.models import Transaccion, ConfiguracionComision, TasaDeCambio
from .datos_historial import HistorialDatosMixin, Usuario, fecha_local

URL = reverse('historial_transacciones')


class BaseHistorialTestCase(HistorialDatosMixin, TestCase):
    """Clase base que asegura la inyección de comisiones para las transacciones."""
    
    def setUp(self):
        super().setUp()
        
        ConfiguracionComision.objects.get_or_create(
            categoria=Cliente.Categoria.MINORISTA,
            defaults={'porcentaje': Decimal('2.00')}
        )
        ConfiguracionComision.objects.get_or_create(
            categoria=Cliente.Categoria.VIP,
            defaults={'porcentaje': Decimal('1.00')}
        )
        
        self.tasa_usd, _ = TasaDeCambio.objects.get_or_create(
            moneda=self.usd,
            defaults={
                'tasa_base': Decimal('7500.00'),
                'margen_compra': Decimal('50.00'),
                'margen_venta': Decimal('50.00')
            }
        )

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


class HistorialAccesoTestCase(BaseHistorialTestCase):
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

    def test_no_ve_transacciones_de_un_cliente_no_asociado(self):
        """El usuario A solo ve las transacciones de su cliente, nunca las del cliente B."""
        propia = self.crear_transaccion(cliente=self.cliente_a)
        self.crear_transaccion(cliente=self.cliente_b)
        self.client.force_login(self.usuario_a)

        response = self.client.get(URL)
        self.assertEqual(list(response.context['page_obj']), [propia])
        self.assertNotContains(response, 'Empresa B S.A.')
        self.assertNotContains(response, '**** 9999')

    def test_cliente_ajeno_en_la_sesion_no_expone_datos(self):
        """Si la sesión tiene el id de un cliente no asociado, se ignora y se usa uno propio."""
        propia = self.crear_transaccion(cliente=self.cliente_a)
        self.crear_transaccion(cliente=self.cliente_b)
        self.client.force_login(self.usuario_a)
        session = self.client.session
        session['ge_active_client'] = str(self.cliente_b.id)
        session.save()

        response = self.client.get(URL)
        self.assertEqual(response.context['cliente'], self.cliente_a)
        self.assertEqual(list(response.context['page_obj']), [propia])
        self.assertEqual(self.client.session['ge_active_client'], str(self.cliente_a.id))

    def test_forzar_medio_de_pago_ajeno_en_url_no_expone_datos(self):
        """Enviar el id de un medio de pago ajeno no muestra transacciones ajenas."""
        self.crear_transaccion(cliente=self.cliente_a)
        ajena = self.crear_transaccion(cliente=self.cliente_b)
        self.client.force_login(self.usuario_a)

        response = self.client.get(URL, {'medio_pago': self.tarjeta_b.pk})
        self.assertIn('medio_pago', response.context['form'].errors)
        self.assertNotIn(ajena, list(response.context['page_obj']))

    def test_forzar_cajero_u_operador_ajeno_en_url_no_expone_datos(self):
        """Enviar el id de un cajero u operador que solo actuó para el cliente B no muestra sus transacciones."""
        cajero_b = Usuario.objects.create_user(username='cajero_b', roles=['Cajero'])
        self.crear_transaccion(cliente=self.cliente_a)
        ajena = self.crear_transaccion(cliente=self.cliente_b, cajero=cajero_b)
        self.client.force_login(self.usuario_a)

        for campo, valor in [('cajero', cajero_b.pk), ('operado_por', self.usuario_b.pk)]:
            with self.subTest(campo=campo):
                response = self.client.get(URL, {campo: valor})
                self.assertIn(campo, response.context['form'].errors)
                self.assertNotIn(ajena, list(response.context['page_obj']))

    def test_opciones_de_filtro_solo_incluyen_datos_del_cliente_activo(self):
        """Las listas del filtro (medio de pago, moneda, cajero, operado por) no incluyen datos del cliente B."""
        cajero_b = Usuario.objects.create_user(username='cajero_b', roles=['Cajero'])
        self.crear_transaccion(cliente=self.cliente_a)
        self.crear_transaccion(cliente=self.cliente_b, moneda=self.eur, cajero=cajero_b)
        self.client.force_login(self.usuario_a)

        form = self.client.get(URL).context['form']
        self.assertEqual(list(form.fields['medio_pago'].queryset), [self.tarjeta_a])
        self.assertEqual(list(form.fields['moneda'].queryset), [self.usd])
        self.assertEqual(list(form.fields['cajero'].queryset), [self.cajero])
        self.assertEqual(list(form.fields['operado_por'].queryset), [self.usuario_a])


class HistorialClienteActivoTestCase(BaseHistorialTestCase):
    """Pruebas del uso del cliente activo (varios usuarios por cliente y varios clientes por usuario)."""

    def setUp(self):
        """Asocia también al usuario A con el cliente B y crea una transacción para cada cliente."""
        super().setUp()
        UsuarioCliente.objects.create(usuario=self.usuario_a, cliente=self.cliente_b)
        self.t_a = self.crear_transaccion(cliente=self.cliente_a)
        self.t_b = self.crear_transaccion(cliente=self.cliente_b, usuario=self.usuario_a)
        self.client.force_login(self.usuario_a)

    def _activar(self, cliente):
        """Guarda el cliente como activo en la sesión, como lo hace el selector del dashboard."""
        session = self.client.session
        session['ge_active_client'] = str(cliente.id)
        session.save()

    def test_solo_muestra_el_cliente_activo(self):
        """Con dos clientes asociados, solo se listan las transacciones del cliente activo."""
        self._activar(self.cliente_b)
        response = self.client.get(URL)
        self.assertEqual(response.context['cliente'], self.cliente_b)
        self.assertEqual(list(response.context['page_obj']), [self.t_b])

    def test_cambiar_cliente_activo_cambia_el_historial(self):
        """Al cambiar el cliente activo en la sesión, el historial muestra el del nuevo cliente."""
        self._activar(self.cliente_b)
        self.assertEqual(list(self.client.get(URL).context['page_obj']), [self.t_b])
        self._activar(self.cliente_a)
        self.assertEqual(list(self.client.get(URL).context['page_obj']), [self.t_a])

    def test_sin_cliente_activo_usa_uno_propio_y_lo_mantiene(self):
        """Sin cliente activo en la sesión se elige uno de los clientes del usuario y se mantiene en las siguientes visitas."""
        elegido = self.client.get(URL).context['cliente']
        self.assertIn(elegido, [self.cliente_a, self.cliente_b])
        self.assertEqual(self.client.session['ge_active_client'], str(elegido.id))
        self.assertEqual(self.client.get(URL).context['cliente'], elegido)

    def test_indicador_del_cliente_en_pantalla(self):
        """Arriba del historial se indica a qué cliente pertenece."""
        self._activar(self.cliente_b)
        response = self.client.get(URL)
        self.assertContains(response, 'Historial de:')
        self.assertContains(response, '<strong>Empresa B S.A.</strong>', html=True)

    def test_muestra_operaciones_de_otros_usuarios_del_cliente(self):
        """Las operaciones que otro usuario hizo en nombre del cliente activo también se ven, con su operador."""
        self.usuario_b.first_name, self.usuario_b.last_name = 'Juan', 'López'
        self.usuario_b.save()
        de_juan = self.crear_transaccion(cliente=self.cliente_b, usuario=self.usuario_b)
        self._activar(self.cliente_b)

        response = self.client.get(URL)
        self.assertIn(de_juan, list(response.context['page_obj']))
        self.assertContains(response, 'Juan López')

    def test_filtro_operado_por(self):
        """El filtro "Operado por" deja solo las operaciones de ese usuario dentro del cliente activo."""
        de_b = self.crear_transaccion(cliente=self.cliente_b, usuario=self.usuario_b)
        self._activar(self.cliente_b)

        response = self.client.get(URL, {'operado_por': self.usuario_b.pk})
        self.assertEqual(list(response.context['page_obj']), [de_b])
        response = self.client.get(URL, {'operado_por': self.usuario_a.pk})
        self.assertEqual(list(response.context['page_obj']), [self.t_b])


class HistorialSoloLecturaTestCase(BaseHistorialTestCase):
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


class HistorialListadoTestCase(BaseHistorialTestCase):
    """Pruebas del contenido y orden del listado."""

    def test_cliente_sin_transacciones(self):
        """Un cliente sin operaciones ve el listado vacío y el mensaje correspondiente."""
        self.client.force_login(self.usuario_a)
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'operaciones/historial.html')
        self.assertEqual(response.context['total'], 0)
        self.assertContains(response, 'Este cliente todavía no tiene transacciones')

    def test_orden_mas_reciente_primero(self):
        """Las transacciones se listan de la más reciente a la más antigua."""
        antigua = self.crear_transaccion(fecha=fecha_local(2026, 7, 1))
        reciente = self.crear_transaccion(fecha=fecha_local(2026, 9, 20))
        media = self.crear_transaccion(fecha=fecha_local(2026, 8, 10))
        self.client.force_login(self.usuario_a)

        response = self.client.get(URL)
        self.assertEqual(list(response.context['page_obj']), [reciente, media, antigua])

    def test_muestra_los_datos_de_la_transaccion(self):
        """Se muestran fecha, hora, tipo, medio de pago, montos, operador, cajero, estado, factura y dispositivo.

        Los montos usan el formato regional (locale `es`: miles con espacio duro y coma decimal).
        """
        self.crear_transaccion(
            fecha=fecha_local(2026, 9, 15, 14, 30), facturada=True, dispositivo=Transaccion.Dispositivo.IPHONE
        )
        self.client.force_login(self.usuario_a)
        response = self.client.get(URL)

        for texto in ['15/09/2026', '14:30', 'Compra USD', '**** 1234', '765\xa0000,00', 'PYG',
                      '100,00', '<th>Operado por</th>', 'cliente_a', 'María González', 'Confirmada', 'iPhone']:
            with self.subTest(texto=texto):
                self.assertContains(response, texto)

    def test_transaccion_pendiente_sin_cajero(self):
        """Una transacción pendiente se muestra sin cajero asignado."""
        self.crear_transaccion(estado=Transaccion.Estado.PENDIENTE, cajero=None)
        self.client.force_login(self.usuario_a)
        response = self.client.get(URL)
        self.assertContains(response, 'Pendiente')
        self.assertNotContains(response, 'María González')

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