"""
Pruebas del menú lateral para usuarios con varios roles.

Un usuario con más de un rol de Keycloak (por ejemplo, Administrador General
y Cajero) debe ver las secciones de cada rol sin ítems repetidos entre ellas;
un usuario con un solo rol ve el mismo menú de siempre.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase
from django.urls import reverse

from main.views import get_menu_sections, resolve_user_role, resolve_user_roles

Usuario = get_user_model()


class MenuVariosRolesTestCase(TestCase):
    """Pruebas de `resolve_user_roles` y de las secciones del menú por rol."""

    def _usuario_con_roles(self, username, *roles):
        """Crea un usuario con los roles dados como grupos (como los sincroniza Keycloak)."""
        usuario = Usuario.objects.create_user(username=username)
        for rol in roles:
            usuario.groups.add(Group.objects.get_or_create(name=rol)[0])
        return usuario

    def _secciones(self, usuario):
        """Devuelve las secciones del menú del dashboard para el usuario."""
        self.client.force_login(usuario)
        return self.client.get(reverse('dashboard')).context['menu_sections']

    def _por_etiqueta(self, secciones):
        """Devuelve `{etiqueta: [urls]}` de las secciones."""
        return {s['label']: [item['url'] for item in s['items']] for s in secciones}

    def test_resolve_user_roles_devuelve_todos_en_orden_de_prioridad(self):
        """Devuelve todos los roles reconocidos, en orden de prioridad, e ignora los desconocidos."""
        usuario = self._usuario_con_roles('multi', 'Cajero', 'otro-rol', 'Administrador General')
        request = RequestFactory().get('/')
        request.user = usuario
        request.session = {}
        self.assertEqual(resolve_user_roles(request), ['Administrador General', 'Cajero'])
        self.assertEqual(resolve_user_role(request), 'Administrador General')

    def test_override_de_desarrollo(self):
        """El rol simulado en la sesión (`ge_role`) reemplaza a los roles reales."""
        usuario = self._usuario_con_roles('multi', 'Cajero', 'Administrador General')
        request = RequestFactory().get('/')
        request.user = usuario
        request.session = {'ge_role': 'Cajero'}
        self.assertEqual(resolve_user_roles(request), ['Cajero'])

    def test_admin_y_cajero_ve_ambas_secciones(self):
        """Con Administrador General y Cajero se ven Gestión de Caja y Administración."""
        secciones = self._por_etiqueta(self._secciones(
            self._usuario_con_roles('multi', 'Administrador General', 'Cajero')
        ))
        self.assertIn('Gestión de Caja', secciones)
        self.assertIn('Administración', secciones)
        self.assertIn(reverse('caja:apertura_caja'), secciones['Gestión de Caja'])
        self.assertIn(reverse('cajas_bloqueadas'), secciones['Administración'])

    def test_sin_items_repetidos_entre_secciones_de_rol(self):
        """Un ítem que ya está en la sección de un rol no se repite en la del otro."""
        secciones = self._por_etiqueta(self._secciones(
            self._usuario_con_roles('multi', 'Administrador General', 'Cajero')
        ))
        urls_de_roles = secciones['Gestión de Caja'] + secciones['Administración']
        self.assertEqual(len(urls_de_roles), len(set(urls_de_roles)))

    def test_un_solo_rol_mantiene_su_menu(self):
        """Con un solo rol el menú no cambia: el cajero no ve Administración y conserva sus ítems."""
        cajero = self._por_etiqueta(self._secciones(self._usuario_con_roles('cajero', 'Cajero')))
        self.assertNotIn('Administración', cajero)
        self.assertIn('/operaciones/simulador/', cajero['Gestión de Caja'])

        admin = self._por_etiqueta(self._secciones(self._usuario_con_roles('admin', 'Administrador General')))
        self.assertNotIn('Gestión de Caja', admin)
        self.assertIn('/operaciones/simulador/', admin['Administración'])

    def test_compatibilidad_sin_lista_de_roles(self):
        """Llamar a `get_menu_sections` sin `roles` funciona como antes (solo el rol principal)."""
        etiquetas = [s['label'] for s in get_menu_sections('Cajero', None, is_authenticated=True)]
        self.assertIn('Gestión de Caja', etiquetas)
        self.assertNotIn('Administración', etiquetas)

    def test_menu_del_cajero_incluye_apertura_y_cierre(self):
        """La sección Gestión de Caja tiene una sola opción "Apertura y Cierre de Caja" (SCRUM-37/40)."""
        secciones = self._secciones(self._usuario_con_roles('cajero', 'Cajero'))
        caja = next(s for s in secciones if s['label'] == 'Gestión de Caja')
        items = {item['name']: item['url'] for item in caja['items']}
        self.assertEqual(items['Apertura y Cierre de Caja'], reverse('caja:apertura_caja'))
        self.assertNotIn('Apertura de Caja', items)
        self.assertNotIn('Cierre de Caja', items)
