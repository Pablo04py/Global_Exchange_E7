"""Datos y configuración de apoyo para los tests de arqueos (SCRUM-40).

Los tests usan los modelos reales de la app `caja` (SCRUM-36): `Caja` y
`SesionCaja` (el turno del cajero). Solo se simula la función de saldo
registrado, que pertenece a otra historia y todavía no existe.
"""

from django.contrib.auth import get_user_model
from django.utils import timezone

from caja.models import Caja, EstadoCaja, EstadoSesionCaja, SesionCaja

Usuario = get_user_model()

# Configuración de los tests: función de saldo registrado de prueba
CONFIG_PRUEBA = {'ARQUEO_FUNCION_SALDO': 'tests.arqueos.apoyo.saldo_de_prueba'}

# Saldo registrado que devuelve la función de prueba (claves en minúscula y
# montos como texto/entero para verificar que la integración los normaliza).
SALDO_DE_PRUEBA = {'pyg': '5740000', 'USD': 900}


def saldo_de_prueba(turno):
    """Función de saldo registrado de prueba, con la firma esperada `f(turno) -> dict`."""
    return SALDO_DE_PRUEBA


class CajaDePruebaMixin:
    """Crea un cajero con un turno abierto en una caja, otro cajero y un administrador."""

    def setUp(self):
        """Carga los usuarios, la caja "Caja 1 (C1)" y el turno ABIERTO del cajero 1."""
        self.cajero = Usuario.objects.create_user(
            username='cajero1', first_name='María', last_name='González', roles=['Cajero']
        )
        self.otro_cajero = Usuario.objects.create_user(username='cajero2', roles=['Cajero'])
        self.admin = Usuario.objects.create_user(username='admin1', roles=['Administrador General'])
        self.caja = Caja.objects.create(nombre='Caja 1', codigo='C1', estado=EstadoCaja.EN_USO)
        self.turno = SesionCaja.objects.create(
            caja=self.caja, cajero=self.cajero, asignado_por=self.admin,
            estado=EstadoSesionCaja.ABIERTA, monto_inicial=5000000, fecha_apertura=timezone.now(),
        )

    def refrescar(self):
        """Recarga el turno y la caja desde la base de datos."""
        self.turno.refresh_from_db()
        self.caja.refresh_from_db()
