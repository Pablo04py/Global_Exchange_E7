"""Pruebas del envío automático del comprobante al pagar una transacción (SCRUM-23, criterio 1).

Durante los tests Django usa el backend de email `locmem`: los correos quedan
en `mail.outbox` y nunca se envían de verdad.
"""

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase

from clientes.models import UsuarioCliente
from comprobantes.models import EnvioComprobante
from comprobantes.services import encolar_envio, obtener_destinatarios
from operaciones.models import Transaccion
from operaciones.services import cambiar_estado_transaccion

from .apoyo import ComprobantesDatosMixin

Usuario = get_user_model()


class EnvioAlPagarTests(ComprobantesDatosMixin, TestCase):
    """El comprobante se envía cuando la transacción pasa a `PAGADA`."""

    def pagar(self, tx):
        """Confirma el pago y ejecuta los callbacks `on_commit` como si se hubiera hecho commit."""
        with self.captureOnCommitCallbacks(execute=True):
            cambiar_estado_transaccion(tx, Transaccion.Estado.PAGADA, self.cajero, motivo='test')

    def test_al_pagar_envia_un_correo_con_el_pdf_adjunto(self):
        tx = self.crear_pendiente()
        self.pagar(tx)

        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertEqual(correo.to, [self.EMAIL_CLIENTE])
        self.assertIn('Comprobante', correo.subject)
        nombre, contenido, tipo = correo.attachments[0]
        self.assertEqual(nombre, f'comprobante-{tx.id}.pdf')
        self.assertEqual(tipo, 'application/pdf')
        self.assertTrue(contenido.startswith(b'%PDF'))

        envio = EnvioComprobante.objects.get(transaccion=tx)
        self.assertEqual(envio.estado, EnvioComprobante.Estado.ENVIADO)
        self.assertEqual(envio.intentos, 1)
        self.assertIsNotNone(envio.fecha_envio)

    def test_no_envia_si_el_pago_no_llega_a_confirmarse_en_la_base(self):
        """Sin commit (por ejemplo, si la operación hace rollback) no sale ningún correo."""
        tx = self.crear_pendiente()
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            cambiar_estado_transaccion(tx, Transaccion.Estado.PAGADA, self.cajero)
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(EnvioComprobante.objects.exists())

    def test_cancelar_no_envia_comprobante(self):
        tx = self.crear_pendiente()
        with self.captureOnCommitCallbacks(execute=True):
            cambiar_estado_transaccion(tx, Transaccion.Estado.CANCELADA, self.cajero)
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(EnvioComprobante.objects.exists())

    def test_transaccion_creada_ya_pagada_no_envia(self):
        """Los datos de prueba se crean directamente como PAGADA y no deben generar correos."""
        with self.captureOnCommitCallbacks(execute=True):
            self.crear_pendiente(estado=Transaccion.Estado.PAGADA)
        self.assertEqual(len(mail.outbox), 0)

    def test_en_caja_lo_recibe_el_cliente_y_no_el_cajero(self):
        tx = self.crear_pendiente(usuario=self.cajero, canal=Transaccion.Canal.CAJA)
        self.pagar(tx)
        self.assertEqual(mail.outbox[0].to, [self.EMAIL_CLIENTE])

    def test_cliente_sin_emails_no_encola(self):
        self.usuario_a.email = ''
        self.usuario_a.save(update_fields=['email'])
        tx = self.crear_pendiente()
        with self.assertLogs('comprobantes.services', level='WARNING'):
            self.pagar(tx)
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(EnvioComprobante.objects.exists())

    def test_no_se_duplica_el_envio_de_una_misma_transaccion(self):
        tx = self.crear_pendiente()
        self.pagar(tx)
        encolar_envio(tx)
        self.assertEqual(EnvioComprobante.objects.filter(transaccion=tx).count(), 1)
        self.assertEqual(len(mail.outbox), 1)


class DestinatariosTests(ComprobantesDatosMixin, TestCase):
    """Elección de los emails a los que se envía el comprobante."""

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
