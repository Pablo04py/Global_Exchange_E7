"""
Pruebas del punto de conexión con el módulo de caja (`arqueos.integracion`).

Evalúa que el arqueo funcione con el modelo de caja configurado, que avise
cuando las otras historias aún no están disponibles y que normalice el saldo
registrado.
"""

from decimal import Decimal

from django.test import TestCase, override_settings

from arqueos import integracion
from .apoyo import CONFIG_SUSTITUTA, CajaDePruebaMixin


class ModuloNoDisponibleTestCase(TestCase):
    """Con la configuración por defecto (módulo de caja aún no integrado)."""

    def test_modelo_de_caja_no_disponible(self):
        """Si el modelo `caja.Caja` no existe, se informa en lugar de fallar."""
        with self.assertRaises(integracion.ModuloCajaNoDisponible):
            integracion.modelo_caja()

    @override_settings(ARQUEO_FUNCION_SALDO='no_existe.saldo')
    def test_funcion_de_saldo_no_disponible(self):
        """Si la función de saldo registrado no existe, se informa en lugar de fallar."""
        with self.assertRaises(integracion.ModuloCajaNoDisponible):
            integracion.obtener_saldo_registrado(object())


@override_settings(**CONFIG_SUSTITUTA)
class IntegracionConfiguradaTestCase(CajaDePruebaMixin, TestCase):
    """Con la integración apuntando al modelo sustituto."""

    def test_obtiene_solo_la_caja_abierta_asignada(self):
        """Devuelve la caja abierta del cajero y nada para quien no tiene caja."""
        self.assertEqual(integracion.obtener_caja_abierta(self.cajero), self.caja)
        self.assertIsNone(integracion.obtener_caja_abierta(self.otro_cajero))

    def test_caja_no_abierta_no_se_obtiene(self):
        """Una caja en otro estado no se considera abierta."""
        self.caja.tipo = 'BLOQUEADA'
        self.caja.save()
        self.assertIsNone(integracion.obtener_caja_abierta(self.cajero))

    @override_settings(ARQUEO_CAMPO_CAJERO='campo_inexistente')
    def test_campo_mal_configurado(self):
        """Un nombre de campo incorrecto se informa como módulo no disponible."""
        with self.assertRaises(integracion.ModuloCajaNoDisponible):
            integracion.obtener_caja_abierta(self.cajero)

    def test_saldo_registrado_normalizado(self):
        """Los códigos se pasan a mayúscula y los montos a Decimal."""
        self.assertEqual(
            integracion.obtener_saldo_registrado(self.caja),
            {'PYG': Decimal('5740000'), 'USD': Decimal('900')},
        )

    def test_datos_de_caja(self):
        """La foto de la caja incluye identificador, nombre y sucursal."""
        datos = integracion.datos_de_caja(self.caja)
        self.assertEqual(datos['caja_id'], str(self.caja.pk))
        self.assertEqual(datos['sucursal_nombre'], 'Casa Central')

    def test_bloquear_caja(self):
        """Cambia el estado de la caja al valor de bloqueo configurado."""
        integracion.bloquear_caja(self.caja)
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.tipo, 'BLOQUEADA')
