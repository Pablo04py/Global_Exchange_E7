from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from caja.models import Caja, SesionCaja, EstadoCaja, EstadoSesionCaja

User = get_user_model()


class AsignarCajeroViewTestCase(TestCase):

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
        self.caja = Caja.objects.create(
            nombre='Caja Principal',
            codigo='CAJA-01',
            estado=EstadoCaja.DISPONIBLE
        )

    def test_asignar_cajero_exitoso(self):
        """Probar asignación exitosa de caja mediante la vista HTTP."""
        self.client.login(username='admin_test', password='password123')

        response = self.client.post(reverse('caja:asignar_cajero'), {
            'caja': self.caja.id,
            'cajero': self.cajero_user.id
        })

        self.assertEqual(response.status_code, 302)
        sesion = SesionCaja.objects.get(caja=self.caja, cajero=self.cajero_user)
        self.assertEqual(sesion.estado, EstadoSesionCaja.ASIGNADA)

    def test_validar_cajero_con_sesion_activa(self):
        """Probar que no se asigne otra caja si el cajero ya tiene una sesión activa."""
        SesionCaja.objects.create(
            caja=self.caja,
            cajero=self.cajero_user,
            asignado_por=self.admin_user,
            estado=EstadoSesionCaja.ASIGNADA
        )

        otra_caja = Caja.objects.create(
            nombre='Caja Secundaria',
            codigo='CAJA-02',
            estado=EstadoCaja.DISPONIBLE
        )

        self.client.login(username='admin_test', password='password123')
        response = self.client.post(reverse('caja:asignar_cajero'), {
            'caja': otra_caja.id,
            'cajero': self.cajero_user.id
        })

        self.assertEqual(response.status_code, 200)
        
        # Pasamos el formulario extraído del contexto de la respuesta
        form = response.context['form']
        self.assertFormError(
            form,
            'cajero',
            'Este cajero ya tiene una caja asignada o abierta actualmente.'
        )