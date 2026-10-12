"""
Pruebas del punto de conexión con el módulo de caja (`arqueos.integracion`).

Evalúa la conexión con los modelos reales de la app `caja` (SCRUM-36), el
aviso cuando una pieza no está disponible y la normalización del saldo.
"""

from decimal import Decimal

from django.test import TestCase, override_settings

from arqueos import integracion
from caja.models import EstadoCaja, EstadoSesionCaja
from .apoyo import CONFIG_PRUEBA, CajaDePruebaMixin


class ModuloNoDisponibleTestCase(TestCase):
    """Cuando alguna pieza de otra historia no existe."""

    @override_settings(ARQUEO_MODELO_TURNO='no_existe.Turno')
    def test_modelo_de_turno_no_disponible(self):
        """Si el modelo de turno no existe, se informa en lugar de fallar."""
        with self.assertRaises(integracion.ModuloCajaNoDisponible):
            integracion.modelo_turno()

    @override_settings(ARQUEO_FUNCION_SALDO='no_existe.saldo')
    def test_funcion_de_saldo_no_disponible(self):
        """Si la función de saldo registrado no existe, se informa en lugar de fallar."""
        with self.assertRaises(integracion.ModuloCajaNoDisponible):
            integracion.obtener_saldo_registrado(object())


@override_settings(**CONFIG_PRUEBA)
class IntegracionConCajaTestCase(CajaDePruebaMixin, TestCase):
    """Con los modelos reales de la app caja."""

    def test_usa_la_sesion_de_caja_por_defecto(self):
        """Por defecto el turno es `caja.SesionCaja`."""
        self.assertEqual(integracion.modelo_turno()._meta.label, 'caja.SesionCaja')

    def test_obtiene_solo_el_turno_abierto_del_cajero(self):
        """Devuelve el turno ABIERTO del cajero y nada para quien no tiene turno."""
        self.assertEqual(integracion.obtener_turno_abierto(self.cajero), self.turno)
        self.assertIsNone(integracion.obtener_turno_abierto(self.otro_cajero))

    def test_turno_no_abierto_no_se_obtiene(self):
        """Un turno ASIGNADO o CERRADO no se considera abierto."""
        for estado in [EstadoSesionCaja.ASIGNADA, EstadoSesionCaja.CERRADA]:
            with self.subTest(estado=estado):
                self.turno.estado = estado
                self.turno.save()
                self.assertIsNone(integracion.obtener_turno_abierto(self.cajero))

    @override_settings(ARQUEO_CAMPO_CAJERO='campo_inexistente')
    def test_campo_mal_configurado(self):
        """Un nombre de campo incorrecto se informa como módulo no disponible."""
        with self.assertRaises(integracion.ModuloCajaNoDisponible):
            integracion.obtener_turno_abierto(self.cajero)

    def test_saldo_registrado_normalizado(self):
        """Los códigos se pasan a mayúscula y los montos a Decimal."""
        self.assertEqual(
            integracion.obtener_saldo_registrado(self.turno),
            {'PYG': Decimal('5740000'), 'USD': Decimal('900')},
        )

    def test_datos_de_caja(self):
        """La foto toma la caja del turno; la sucursal queda vacía mientras no exista."""
        self.assertEqual(integracion.datos_de_caja(self.turno), {
            'caja_id': str(self.caja.pk), 'caja_nombre': 'Caja 1 (C1)', 'sucursal_nombre': '',
        })

    def test_cerrar_turno_y_bloquear_caja(self):
        """El turno pasa a CERRADA con fecha de cierre y la caja a INACTIVA."""
        integracion.cerrar_turno_y_bloquear_caja(self.turno)
        self.refrescar()
        self.assertEqual(self.turno.estado, EstadoSesionCaja.CERRADA)
        self.assertIsNotNone(self.turno.fecha_cierre)
        self.assertEqual(self.caja.estado, EstadoCaja.INACTIVA)
