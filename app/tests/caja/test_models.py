from django.test import TestCase
from django.contrib.auth import get_user_model
from caja.models import Caja, SesionCaja, EstadoCaja, EstadoSesionCaja

User = get_user_model()


class CajaModelsTestCase(TestCase):

    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='password123',
            is_staff=True
        )
        self.cajero_user = User.objects.create_user(
            username='cajero_test',
            password='password123'
        )

    def test_creacion_caja(self):
        """Probar creación de caja en estado disponible."""
        caja = Caja.objects.create(
            nombre='Caja Central',
            codigo='CAJA-01',
            estado=EstadoCaja.DISPONIBLE
        )
        self.assertEqual(str(caja), 'Caja Central (CAJA-01)')
        self.assertTrue(caja.activa)

    def test_creacion_sesion_caja_asignada(self):
        """Probar creación de asignación de sesión de caja."""
        caja = Caja.objects.create(
            nombre='Caja Auxiliar',
            codigo='CAJA-02',
            estado=EstadoCaja.DISPONIBLE
        )
        sesion = SesionCaja.objects.create(
            caja=caja,
            cajero=self.cajero_user,
            asignado_por=self.admin_user,
            estado=EstadoSesionCaja.ASIGNADA
        )
        self.assertEqual(sesion.estado, EstadoSesionCaja.ASIGNADA)
        self.assertEqual(sesion.cajero, self.cajero_user)
        self.assertEqual(sesion.asignado_por, self.admin_user)