"""
Módulo de pruebas unitarias de integración para las vistas de Medios de Pago (mpagos).

Evalúa respuestas HTTP, control de autenticación y lógica de borrado lógico.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from mpagos.models import MedioPago

Usuario = get_user_model()


class MedioPagoViewsTestCase(TestCase):
    """Pruebas de vistas y controladores del CRUD de Medios de Pago."""

    def setUp(self):
        """Configuración de cliente HTTP y usuario autenticado."""
        self.client = Client()
        self.usuario = Usuario.objects.create_user(
            username="usuario_pagos",
            password="password123"
        )
        self.medio = MedioPago.objects.create(
            usuario=self.usuario,
            tipo="TARJETA",
            nombre_titular="Carlos Gómez",
            numero_enmascarado="**** **** **** 1234"
        )

    def test_listar_medios_requiere_login(self):
        """Verifica que usuarios anónimos sean redirigidos al login (HTTP 302)."""
        response = self.client.get(reverse('mpagos:listar'))
        self.assertEqual(response.status_code, 302)

    def test_listar_medios_pago_usuario_autenticado(self):
        """Verifica que un usuario autenticado pueda acceder a su lista de medios de pago."""
        # Autenticar la sesión del cliente
        self.client.login(username="usuario_pagos", password="password123")
        response = self.client.get(reverse('mpagos:listar'))

        # Validar respuesta 200 y presencia del contexto
        self.assertEqual(response.status_code, 200)
        self.assertIn('medios', response.context)
        self.assertEqual(len(response.context['medios']), 1)

    def test_crear_medio_pago_post_exitoso(self):
        """Verifica la creación de un medio de pago mediante petición POST."""
        self.client.login(username="usuario_pagos", password="password123")
        data = {
            'tipo': 'SIPAP',
            'nombre_titular': 'Carlos Gómez',
            'banco_emisor': 'Continental',
            'numero_enmascarado': 'Alias SIPAP 1234',
            'es_predeterminado': True
        }
        response = self.client.post(reverse('mpagos:crear'), data)

        # Debe redirigir al listado tras guardar exitosamente
        self.assertRedirects(response, reverse('mpagos:listar'))
        self.assertEqual(MedioPago.objects.filter(usuario=self.usuario).count(), 2)

    def test_eliminar_medio_pago_borrado_logico(self):
        """Verifica que la vista eliminar aplique borrado lógico (activo=False)."""
        self.client.login(username="usuario_pagos", password="password123")
        response = self.client.post(reverse('mpagos:eliminar', kwargs={'pk': self.medio.pk}))

        # Validar redirección y cambio de estado a inactivo en base de datos
        self.assertRedirects(response, reverse('mpagos:listar'))
        self.medio.refresh_from_db()
        self.assertFalse(self.medio.activo)

    def test_editar_medio_pago_post_exitoso(self):
        """Verifica la edición de un medio de pago existente mediante petición POST."""
        # Autenticar la sesión del cliente de prueba
        self.client.login(username="usuario_pagos", password="password123")
        
        # Datos modificados
        data = {
            'tipo': 'TARJETA',
            'nombre_titular': 'Carlos Gómez Editado',
            'banco_emisor': 'Banco Itaú',
            'numero_enmascarado': '**** **** **** 9999',
            'es_predeterminado': True
        }
        
        # Enviar petición POST de edición
        response = self.client.post(reverse('mpagos:editar', kwargs={'pk': self.medio.pk}), data)

        # Validar redirección y actualización en base de datos
        self.assertRedirects(response, reverse('mpagos:listar'))
        self.medio.refresh_from_db()
        self.assertEqual(self.medio.nombre_titular, 'Carlos Gómez Editado')
        self.assertTrue(self.medio.es_predeterminado)