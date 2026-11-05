"""Pruebas del correo al que se envía la factura: el del cliente que hizo la compra (SCRUM-23)."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from clientes.models import Cliente, UsuarioCliente
from comprobantes.destinatarios import email_receptor_factura
from comprobantes.services import obtener_destinatarios
from facturacion.services.factura_builder import construir_receptor
from operaciones.models import Transaccion

from .apoyo import ComprobantesDatosMixin

Usuario = get_user_model()


class EmailReceptorTests(ComprobantesDatosMixin, TestCase):
    """`email_receptor_factura` elige el email de la cuenta del cliente, nunca el del cajero."""

    def asociar(self, username, email, rol=UsuarioCliente.RolCliente.OPERADOR, **campos):
        """Crea un usuario y lo asocia a `cliente_a`."""
        usuario = Usuario.objects.create_user(username=username, password='x', email=email, **campos)
        UsuarioCliente.objects.create(usuario=usuario, cliente=self.cliente_a, rol_cliente=rol)
        return usuario

    def en_caja(self, cliente=None):
        """Transacción de caja: la registra el cajero, que no está asociado al cliente."""
        return self.crear_pendiente(cliente=cliente or self.cliente_a, usuario=self.cajero,
                                    canal=Transaccion.Canal.CAJA, estado=Transaccion.Estado.PAGADA)

    def test_en_web_es_el_email_del_usuario_que_compro(self):
        otro = self.asociar('socio', 'socio@cliente.test', rol=UsuarioCliente.RolCliente.ADMIN)
        tx = self.crear_pendiente(usuario=otro)
        self.assertEqual(email_receptor_factura(tx), 'socio@cliente.test')

    def test_en_caja_es_la_cuenta_del_cliente_y_no_el_cajero(self):
        self.assertEqual(email_receptor_factura(self.en_caja()), self.EMAIL_CLIENTE)

    def test_en_caja_prefiere_la_cuenta_admin_del_cliente(self):
        self.asociar('admin_cliente', 'admin@cliente.test', rol=UsuarioCliente.RolCliente.ADMIN)
        self.assertEqual(email_receptor_factura(self.en_caja()), 'admin@cliente.test')

    def test_sin_admin_usa_la_asociacion_mas_antigua(self):
        self.asociar('segundo', 'segundo@cliente.test')
        self.assertEqual(email_receptor_factura(self.en_caja()), self.EMAIL_CLIENTE)

    def test_ignora_usuarios_inactivos_o_sin_email(self):
        self.usuario_a.email = ''
        self.usuario_a.save(update_fields=['email'])
        self.asociar('baja', 'baja@cliente.test', rol=UsuarioCliente.RolCliente.ADMIN, is_active=False)
        self.asociar('activo', 'activo@cliente.test')
        self.assertEqual(email_receptor_factura(self.en_caja()), 'activo@cliente.test')

    def test_cliente_sin_cuentas_usa_el_usuario_de_la_transaccion(self):
        """Comportamiento original de SCRUM-56 cuando el cliente no tiene ninguna cuenta con email."""
        cliente = Cliente.objects.create(tipo_persona=Cliente.TipoPersona.FISICA,
                                         nombre_o_denominacion='Sin cuenta', documento='999')
        self.assertEqual(email_receptor_factura(self.en_caja(cliente)), 'cajero@globalexchange.test')

    def test_obtener_destinatarios_devuelve_ese_email(self):
        self.assertEqual(obtener_destinatarios(self.en_caja()), [self.EMAIL_CLIENTE])


class ReceptorDelDocumentoElectronicoTests(ComprobantesDatosMixin, TestCase):
    """El Documento Electrónico de SCRUM-56 lleva ese email: Factura Segura envía ahí el KuDE y el XML."""

    def test_en_caja_el_dEmailRec_es_el_del_cliente(self):
        tx = self.crear_pendiente(usuario=self.cajero, canal=Transaccion.Canal.CAJA,
                                  estado=Transaccion.Estado.PAGADA)
        self.assertEqual(construir_receptor(tx)['dEmailRec'], self.EMAIL_CLIENTE)

    def test_sin_ningun_email_no_se_puede_construir(self):
        self.usuario_a.email = ''
        self.usuario_a.save(update_fields=['email'])
        with self.assertRaises(ValidationError):
            construir_receptor(self.crear_pendiente(estado=Transaccion.Estado.PAGADA))
