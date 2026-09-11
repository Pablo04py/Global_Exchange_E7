"""
Módulo de pruebas unitarias para los modelos de Medios de Pago (mpagos).

Valida la instanciación, valores por defecto y representación en texto de MedioPago.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from mpagos.models import MedioPago

Usuario = get_user_model()


class MedioPagoModelTestCase(TestCase):
    """Pruebas unitarias para la entidad MedioPago."""

    def setUp(self):
        """Inicialización de datos de prueba para el entorno de test."""
        self.usuario = Usuario.objects.create_user(
            username="cliente_test",
            password="password123"
        )

    def test_creacion_medio_pago_exitoso(self):
        """Verifica la creación y persistencia de un medio de pago en la base de datos."""
        # Instanciar e insertar un registro válido de medio de pago
        medio = MedioPago.objects.create(
            usuario=self.usuario,
            tipo="SIPAP",
            nombre_titular="Juan Pérez",
            banco_emisor="Itaú",
            numero_enmascarado="**** 4321",
            es_predeterminado=True
        )

        # Verificación de datos guardados correctamente en los campos
        self.assertEqual(medio.tipo, "SIPAP")
        self.assertEqual(medio.nombre_titular, "Juan Pérez")
        self.assertTrue(medio.es_predeterminado)
        self.assertTrue(medio.activo)
        
        # Verificación del método __str__ para pdoc e interfaz
        self.assertIn("Transferencia Bancaria (SIPAP)", str(medio))

    def test_valores_por_defecto_medio_pago(self):
        """Verifica que las banderas activo y es_predeterminado tomen sus valores por defecto."""
        # Crear objeto omitiendo campos booleanos opcionales
        medio = MedioPago.objects.create(
            usuario=self.usuario,
            tipo="EFECTIVO",
            nombre_titular="María López",
            numero_enmascarado="Efectivo en Caja"
        )

        # Comprobar asignación de valores predeterminados
        self.assertFalse(medio.es_predeterminado)
        self.assertTrue(medio.activo)