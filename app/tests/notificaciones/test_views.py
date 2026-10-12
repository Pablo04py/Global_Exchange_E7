"""Pruebas de las vistas de la aplicación notificaciones."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from notificaciones.models import (
    Notificacion,
    NotificacionUsuario,
)


Usuario = get_user_model()


def crear_usuario(username, email):
    """
    Crea un usuario compatible con el modelo personalizado del proyecto.
    """

    datos = {
        'username': username,
        'email': email,
    }

    nombres_campos = {
        campo.name
        for campo in Usuario._meta.fields
    }

    if 'keycloak_id' in nombres_campos:
        datos['keycloak_id'] = f'kc-{username}'

    if 'roles' in nombres_campos:
        datos['roles'] = []

    return Usuario.objects.create_user(
        password='test1234',
        **datos
    )


class MarcarLeidaViewTests(TestCase):
    """Pruebas para marcar una notificación individual como leída."""

    def setUp(self):
        self.usuario = crear_usuario(
            username='usuario1',
            email='usuario1@test.com'
        )

        self.otro_usuario = crear_usuario(
            username='usuario2',
            email='usuario2@test.com'
        )

        self.notificacion = Notificacion.objects.create(
            tipo=Notificacion.Tipo.TASA_CAMBIO,
            titulo='Cotización USD actualizada',
            mensaje='Compra y venta modificadas.'
        )

        self.item = NotificacionUsuario.objects.create(
            notificacion=self.notificacion,
            usuario=self.usuario
        )

        self.url = reverse(
            'notificaciones:marcar_leida',
            args=[self.item.id]
        )

    def test_requiere_autenticacion(self):
        """
        Un usuario no autenticado no debe poder marcar
        notificaciones como leídas.
        """

        response = self.client.post(
            self.url
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertIn(
            '/oidc/',
            response.url
        )

    def test_no_acepta_get(self):
        """La vista debe aceptar únicamente peticiones POST."""

        self.client.force_login(
            self.usuario
        )

        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.status_code,
            405
        )

    def test_marca_notificacion_como_leida(self):
        """
        El propietario de la notificación puede marcarla como leída.
        """

        self.client.force_login(
            self.usuario
        )

        response = self.client.post(
            self.url
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.item.refresh_from_db()

        self.assertTrue(
            self.item.leida
        )

        self.assertIsNotNone(
            self.item.fecha_lectura
        )

    def test_respuesta_json_correcta(self):
        """La vista debe devolver status ok y cantidad pendiente."""

        # Segunda notificación que seguirá pendiente.
        segunda_notificacion = Notificacion.objects.create(
            tipo=Notificacion.Tipo.TASA_CAMBIO,
            titulo='Cotización EUR actualizada',
            mensaje='Actualización EUR.'
        )

        NotificacionUsuario.objects.create(
            notificacion=segunda_notificacion,
            usuario=self.usuario
        )

        self.client.force_login(
            self.usuario
        )

        response = self.client.post(
            self.url
        )

        datos = response.json()

        self.assertEqual(
            datos['status'],
            'ok'
        )

        self.assertEqual(
            datos['pendientes'],
            1
        )

    def test_no_puede_marcar_notificacion_de_otro_usuario(self):
        """
        Un usuario no debe poder modificar una notificación
        asignada a otro usuario.
        """

        self.client.force_login(
            self.otro_usuario
        )

        response = self.client.post(
            self.url
        )

        self.assertEqual(
            response.status_code,
            404
        )

        self.item.refresh_from_db()

        self.assertFalse(
            self.item.leida
        )

    def test_marcar_notificacion_ya_leida_es_idempotente(self):
        """
        Marcar nuevamente una notificación ya leída no debe producir errores.
        """

        self.client.force_login(
            self.usuario
        )

        primera_respuesta = self.client.post(
            self.url
        )

        self.item.refresh_from_db()

        primera_fecha = self.item.fecha_lectura

        segunda_respuesta = self.client.post(
            self.url
        )

        self.item.refresh_from_db()

        self.assertEqual(
            primera_respuesta.status_code,
            200
        )

        self.assertEqual(
            segunda_respuesta.status_code,
            200
        )

        self.assertEqual(
            self.item.fecha_lectura,
            primera_fecha
        )


class MarcarTodasLeidasViewTests(TestCase):
    """Pruebas para marcar todas las notificaciones del usuario."""

    def setUp(self):
        self.usuario = crear_usuario(
            username='usuario_todas',
            email='todas@test.com'
        )

        self.otro_usuario = crear_usuario(
            username='usuario_ajeno',
            email='ajeno@test.com'
        )

        self.url = reverse(
            'notificaciones:marcar_todas_leidas'
        )

        for numero in range(3):

            notificacion = Notificacion.objects.create(
                tipo=Notificacion.Tipo.TASA_CAMBIO,
                titulo=f'Notificación {numero}',
                mensaje=f'Mensaje {numero}'
            )

            NotificacionUsuario.objects.create(
                notificacion=notificacion,
                usuario=self.usuario
            )

        notificacion_ajena = Notificacion.objects.create(
            tipo=Notificacion.Tipo.SISTEMA,
            titulo='Notificación ajena',
            mensaje='No debe modificarse.'
        )

        self.item_ajeno = NotificacionUsuario.objects.create(
            notificacion=notificacion_ajena,
            usuario=self.otro_usuario
        )

    def test_requiere_autenticacion(self):
        """Un anónimo no puede marcar todas como leídas."""

        response = self.client.post(
            self.url
        )

        self.assertEqual(
            response.status_code,
            302
        )

    def test_no_acepta_get(self):
        """La vista solo debe aceptar POST."""

        self.client.force_login(
            self.usuario
        )

        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.status_code,
            405
        )

    def test_marca_todas_las_notificaciones_del_usuario(self):
        """
        Debe marcar como leídas todas las notificaciones
        pendientes del usuario autenticado.
        """

        self.client.force_login(
            self.usuario
        )

        response = self.client.post(
            self.url
        )

        self.assertEqual(
            response.status_code,
            200
        )

        pendientes = (
            NotificacionUsuario.objects
            .filter(
                usuario=self.usuario,
                leida=False
            )
            .count()
        )

        self.assertEqual(
            pendientes,
            0
        )

    def test_asigna_fecha_lectura_a_todas(self):
        """
        Todas las notificaciones procesadas deben recibir fecha_lectura.
        """

        self.client.force_login(
            self.usuario
        )

        self.client.post(
            self.url
        )

        items = (
            NotificacionUsuario.objects
            .filter(usuario=self.usuario)
        )

        for item in items:
            self.assertTrue(
                item.leida
            )

            self.assertIsNotNone(
                item.fecha_lectura
            )

    def test_no_modifica_notificaciones_de_otro_usuario(self):
        """
        Marcar todas como leídas no debe afectar las notificaciones
        pertenecientes a otros usuarios.
        """

        self.client.force_login(
            self.usuario
        )

        self.client.post(
            self.url
        )

        self.item_ajeno.refresh_from_db()

        self.assertFalse(
            self.item_ajeno.leida
        )

        self.assertIsNone(
            self.item_ajeno.fecha_lectura
        )

    def test_respuesta_json_indica_cero_pendientes(self):
        """La respuesta AJAX debe devolver pendientes igual a cero."""

        self.client.force_login(
            self.usuario
        )

        response = self.client.post(
            self.url
        )

        datos = response.json()

        self.assertEqual(
            datos['status'],
            'ok'
        )

        self.assertEqual(
            datos['pendientes'],
            0
        )