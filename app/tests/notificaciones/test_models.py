"""Pruebas unitarias para los modelos de notificaciones."""

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from notificaciones.models import Notificacion, NotificacionUsuario


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

    # Compatibilidad con el usuario sincronizado con Keycloak.
    if 'keycloak_id' in nombres_campos:
        datos['keycloak_id'] = f'kc-{username}'

    if 'roles' in nombres_campos:
        datos['roles'] = []

    return Usuario.objects.create_user(
        password='test1234',
        **datos
    )


class NotificacionModelTests(TestCase):
    """Pruebas del modelo Notificacion."""

    def setUp(self):
        self.usuario = crear_usuario(
            username='analista_test',
            email='analista@test.com'
        )

    def test_crear_notificacion(self):
        """Debe poder crear una notificación correctamente."""

        notificacion = Notificacion.objects.create(
            tipo=Notificacion.Tipo.TASA_CAMBIO,
            titulo='Cotización USD actualizada',
            mensaje='Compra: G. 7.600 → G. 7.650',
            creada_por=self.usuario
        )

        self.assertIsNotNone(notificacion.id)

        self.assertEqual(
            notificacion.tipo,
            Notificacion.Tipo.TASA_CAMBIO
        )

        self.assertEqual(
            notificacion.titulo,
            'Cotización USD actualizada'
        )

        self.assertEqual(
            notificacion.creada_por,
            self.usuario
        )

        self.assertIsNotNone(
            notificacion.fecha_creacion
        )

    def test_str_notificacion_devuelve_titulo(self):
        """__str__ debe devolver el título de la notificación."""

        notificacion = Notificacion.objects.create(
            tipo=Notificacion.Tipo.SISTEMA,
            titulo='Aviso del sistema',
            mensaje='Mensaje de prueba',
            creada_por=self.usuario
        )

        self.assertEqual(
            str(notificacion),
            'Aviso del sistema'
        )

    def test_creada_por_puede_ser_null(self):
        """
        Una notificación del sistema puede existir sin usuario creador.
        """

        notificacion = Notificacion.objects.create(
            tipo=Notificacion.Tipo.SISTEMA,
            titulo='Mantenimiento',
            mensaje='Sistema en mantenimiento.'
        )

        self.assertIsNone(
            notificacion.creada_por
        )

    def test_eliminar_creador_no_elimina_notificacion(self):
        """
        Al eliminar el usuario creador, la notificación debe conservarse
        porque creada_por utiliza SET_NULL.
        """

        notificacion = Notificacion.objects.create(
            tipo=Notificacion.Tipo.TASA_CAMBIO,
            titulo='Cotización EUR actualizada',
            mensaje='Cambio de prueba',
            creada_por=self.usuario
        )

        notificacion_id = notificacion.id

        self.usuario.delete()

        notificacion.refresh_from_db()

        self.assertEqual(
            notificacion.id,
            notificacion_id
        )

        self.assertIsNone(
            notificacion.creada_por
        )


class NotificacionUsuarioModelTests(TestCase):
    """Pruebas del modelo NotificacionUsuario."""

    def setUp(self):
        self.usuario = crear_usuario(
            username='usuario_test',
            email='usuario@test.com'
        )

        self.notificacion = Notificacion.objects.create(
            tipo=Notificacion.Tipo.TASA_CAMBIO,
            titulo='Cotización USD actualizada',
            mensaje='Compra y venta actualizadas.'
        )

    def test_notificacion_usuario_se_crea_no_leida(self):
        """
        Una notificación asignada a un usuario debe comenzar como no leída.
        """

        item = NotificacionUsuario.objects.create(
            notificacion=self.notificacion,
            usuario=self.usuario
        )

        self.assertFalse(item.leida)

        self.assertIsNone(
            item.fecha_lectura
        )

    def test_str_notificacion_usuario_no_leida(self):
        """__str__ debe indicar que la notificación no está leída."""

        item = NotificacionUsuario.objects.create(
            notificacion=self.notificacion,
            usuario=self.usuario
        )

        texto = str(item)

        self.assertIn(
            self.notificacion.titulo,
            texto
        )

        self.assertIn(
            'No leída',
            texto
        )

    def test_no_permite_duplicar_notificacion_para_mismo_usuario(self):
        """
        La restricción única debe impedir asignar dos veces
        la misma notificación al mismo usuario.
        """

        NotificacionUsuario.objects.create(
            notificacion=self.notificacion,
            usuario=self.usuario
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                NotificacionUsuario.objects.create(
                    notificacion=self.notificacion,
                    usuario=self.usuario
                )

    def test_misma_notificacion_puede_ir_a_distintos_usuarios(self):
        """Una misma notificación puede asignarse a varios usuarios."""

        otro_usuario = crear_usuario(
            username='otro_usuario',
            email='otro@test.com'
        )

        NotificacionUsuario.objects.create(
            notificacion=self.notificacion,
            usuario=self.usuario
        )

        NotificacionUsuario.objects.create(
            notificacion=self.notificacion,
            usuario=otro_usuario
        )

        cantidad = (
            NotificacionUsuario.objects
            .filter(notificacion=self.notificacion)
            .count()
        )

        self.assertEqual(
            cantidad,
            2
        )

    def test_eliminar_notificacion_elimina_relacion_usuario(self):
        """
        Al borrar Notificacion debe borrarse también NotificacionUsuario
        mediante CASCADE.
        """

        item = NotificacionUsuario.objects.create(
            notificacion=self.notificacion,
            usuario=self.usuario
        )

        item_id = item.id

        self.notificacion.delete()

        self.assertFalse(
            NotificacionUsuario.objects
            .filter(id=item_id)
            .exists()
        )