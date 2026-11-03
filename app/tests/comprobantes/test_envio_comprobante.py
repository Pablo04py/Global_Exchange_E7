"""Pruebas del envío automático del KuDE al aprobarse la factura (SCRUM-23, criterio 1).

Durante los tests Django usa el backend de email `locmem`: los correos quedan
en `mail.outbox` y nunca se envían de verdad. Factura Segura se simula con `patch`.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from clientes.models import UsuarioCliente
from comprobantes.models import EnvioComprobante
from comprobantes.services import encolar_envio, obtener_destinatarios, procesar_pendientes
from facturacion.models import FacturaElectronica
from facturacion.services.emision import sincronizar_estado_sifen
from operaciones.models import Transaccion
from operaciones.services import cambiar_estado_transaccion

from .apoyo import KUDE_MOCK, ComprobantesDatosMixin

Usuario = get_user_model()

DESCARGAR_KUDE = 'comprobantes.services.FacturaSeguraService.descargar_kude'


class EncoladoTests(ComprobantesDatosMixin, TestCase):
    """El envío se encola cuando la factura queda `APROBADA` y solo en ese caso."""

    def test_factura_aprobada_encola_un_envio_pendiente(self):
        factura = self.aprobar(self.crear_factura())

        envio = EnvioComprobante.objects.get(factura=factura)
        self.assertEqual(envio.estado, EnvioComprobante.Estado.PENDIENTE)
        self.assertEqual(envio.destinatarios, [self.EMAIL_CLIENTE])
        self.assertEqual(envio.intentos, 0)
        # El correo no sale en el mismo guardado: lo manda el mailer.
        self.assertEqual(len(mail.outbox), 0)

    def test_otros_estados_no_encolan(self):
        for estado in (FacturaElectronica.Estado.EMITIDA, FacturaElectronica.Estado.RECHAZADA,
                       FacturaElectronica.Estado.ERROR):
            with self.subTest(estado=estado), self.captureOnCommitCallbacks(execute=True):
                self.crear_factura(estado=estado)
        self.assertFalse(EnvioComprobante.objects.exists())

    def test_no_encola_si_la_aprobacion_no_llega_a_guardarse(self):
        """Sin commit (por ejemplo, si hay rollback) no se encola nada."""
        factura = self.crear_factura()
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            factura.estado = FacturaElectronica.Estado.APROBADA
            factura.save()
        self.assertEqual(len(callbacks), 1)
        self.assertFalse(EnvioComprobante.objects.exists())

    def test_guardar_dos_veces_la_factura_aprobada_no_duplica_el_envio(self):
        factura = self.aprobar(self.crear_factura())
        self.aprobar(factura)
        self.assertEqual(EnvioComprobante.objects.filter(factura=factura).count(), 1)

    @override_settings(FACTURACION_EMISION_AUTOMATICA=False, COMPROBANTES_SIMULAR_FACTURA=False)
    def test_pagar_la_transaccion_no_envia_correo(self):
        """Sin modo simulación, el correo depende de la factura aprobada, no del pago."""
        tx = self.crear_pendiente()
        with self.captureOnCommitCallbacks(execute=True):
            cambiar_estado_transaccion(tx, Transaccion.Estado.PAGADA, self.cajero)
        self.assertFalse(EnvioComprobante.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_cliente_sin_emails_no_encola(self):
        self.usuario_a.email = ''
        self.usuario_a.save(update_fields=['email'])
        with self.assertLogs('comprobantes.services', level='WARNING'):
            self.aprobar(self.crear_factura())
        self.assertFalse(EnvioComprobante.objects.exists())

    def test_en_caja_lo_recibe_el_cliente_y_no_el_cajero(self):
        tx = self.crear_pendiente(usuario=self.cajero, canal=Transaccion.Canal.CAJA,
                                  estado=Transaccion.Estado.PAGADA)
        factura = self.aprobar(self.crear_factura(tx))
        self.assertEqual(factura.envio_email.destinatarios, [self.EMAIL_CLIENTE])

    @patch('facturacion.services.emision.FacturaSeguraService.get_estado_sifen')
    def test_la_aprobacion_desde_sifen_encola_el_envio(self, mock_estado):
        """Integración con SCRUM-56: `sincronizar_estado_sifen` aprueba la factura y se encola el envío."""
        mock_estado.return_value = {
            'code': 0, 'description': 'OK', 'operation_info': {'id': 'mock-sifen'},
            'results': [{'estado_sifen': 'Aprobado', 'desc_sifen': '0260 - Aprobado', 'error_sifen': ''}],
        }
        factura = self.crear_factura()
        with self.captureOnCommitCallbacks(execute=True):
            sincronizar_estado_sifen(factura)
        self.assertTrue(EnvioComprobante.objects.filter(factura=factura).exists())


class EnvioTests(ComprobantesDatosMixin, TestCase):
    """El comando del mailer descarga el KuDE y lo manda como adjunto."""

    @patch(DESCARGAR_KUDE, return_value=KUDE_MOCK)
    def test_envia_el_kude_adjunto_a_los_usuarios_del_cliente(self, mock_kude):
        factura = self.aprobar(self.crear_factura())

        resumen = procesar_pendientes()

        self.assertEqual(resumen, {'procesados': 1, 'enviados': 1, 'fallidos': 0})
        mock_kude.assert_called_once_with(ruc_emisor='2595733', cdc=factura.cdc)
        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertEqual(correo.to, [self.EMAIL_CLIENTE])
        self.assertIn(factura.numero_documento, correo.subject)
        self.assertIn(factura.cdc, correo.body)
        self.assertEqual(correo.attachments[0], (f'factura_{factura.numero_documento}.pdf', KUDE_MOCK,
                                                 'application/pdf'))

        envio = factura.envio_email
        envio.refresh_from_db()
        self.assertEqual(envio.estado, EnvioComprobante.Estado.ENVIADO)
        self.assertEqual(envio.intentos, 1)
        self.assertIsNotNone(envio.fecha_envio)

    @patch(DESCARGAR_KUDE, return_value=KUDE_MOCK)
    def test_un_envio_ya_enviado_no_se_vuelve_a_mandar(self, mock_kude):
        factura = self.aprobar(self.crear_factura())
        procesar_pendientes()
        encolar_envio(factura)
        self.assertEqual(procesar_pendientes()['procesados'], 0)
        self.assertEqual(len(mail.outbox), 1)


class DestinatariosTests(ComprobantesDatosMixin, TestCase):
    """Elección de los emails a los que se envía la factura."""

    def test_incluye_a_todos_los_usuarios_activos_del_cliente_sin_repetir(self):
        otro = Usuario.objects.create_user(username='socio', password='x', email='Socio@Cliente.test')
        repetido = Usuario.objects.create_user(username='repetido', password='x', email='ANA@cliente.test')
        inactivo = Usuario.objects.create_user(username='baja', password='x', email='baja@cliente.test',
                                               is_active=False)
        for usuario in (otro, repetido, inactivo):
            UsuarioCliente.objects.create(usuario=usuario, cliente=self.cliente_a)

        tx = self.crear_pendiente()
        self.assertEqual(obtener_destinatarios(tx), ['ana@cliente.test', 'socio@cliente.test'])

    def test_no_incluye_usuarios_de_otros_clientes(self):
        self.usuario_b.email = 'empresa@b.test'
        self.usuario_b.save(update_fields=['email'])
        tx = self.crear_pendiente()
        self.assertNotIn('empresa@b.test', obtener_destinatarios(tx))
