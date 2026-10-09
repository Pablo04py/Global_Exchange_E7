"""Datos y configuración de apoyo para los tests de arqueos (SCRUM-40).

El modelo de caja y el saldo registrado pertenecen a otras historias que aún
no existen. Para probar la integración real, los tests configuran el arqueo
con un modelo sustituto que ya existe en el proyecto (`mpagos.MedioPago`):

- `usuario` hace de cajero asignado,
- `tipo` hace de estado (`EFECTIVO` = abierta),
- `nombre_titular` y `banco_emisor` dan el nombre y la "sucursal".

Esto demuestra que el arqueo se conecta a cualquier modelo solo cambiando la
configuración, que es lo que ocurrirá con el modelo de caja de SCRUM-36/37.
"""

from django.contrib.auth import get_user_model

from mpagos.models import MedioPago

Usuario = get_user_model()

CONFIG_SUSTITUTA = {
    'ARQUEO_MODELO_CAJA': 'mpagos.MedioPago',
    'ARQUEO_CAMPO_CAJERO': 'usuario',
    'ARQUEO_CAMPO_ESTADO': 'tipo',
    'ARQUEO_CAMPO_SUCURSAL': 'banco_emisor',
    'ARQUEO_ESTADO_ABIERTA': 'EFECTIVO',
    'ARQUEO_ESTADO_BLOQUEADA': 'BLOQUEADA',
    'ARQUEO_FUNCION_SALDO': 'tests.arqueos.apoyo.saldo_de_prueba',
}

# Saldo registrado que devuelve la función de prueba (claves en minúscula y
# montos como texto/entero para verificar que la integración los normaliza).
SALDO_DE_PRUEBA = {'pyg': '5740000', 'USD': 900}


def saldo_de_prueba(caja):
    """Función de saldo registrado de prueba, con la firma esperada `f(caja) -> dict`."""
    return SALDO_DE_PRUEBA


class CajaDePruebaMixin:
    """Crea un cajero con una "caja" abierta asignada y otros usuarios de apoyo."""

    def setUp(self):
        """Carga el cajero, su caja abierta, otro cajero y un administrador."""
        self.cajero = Usuario.objects.create_user(
            username='cajero1', first_name='María', last_name='González', roles=['Cajero']
        )
        self.otro_cajero = Usuario.objects.create_user(username='cajero2', roles=['Cajero'])
        self.admin = Usuario.objects.create_user(username='admin1', roles=['Administrador General'])
        self.caja = MedioPago.objects.create(
            usuario=self.cajero, tipo='EFECTIVO', nombre_titular='Caja 1',
            banco_emisor='Casa Central', numero_enmascarado='-',
        )
