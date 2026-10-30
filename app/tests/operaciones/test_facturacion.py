from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import (
    RequestFactory,
    TestCase,
    override_settings,
)

from usuarios.models import Usuario
from clientes.models import Cliente
from mpagos.models import MedioPago

from operaciones.models import (
    LogTransaccion,
    Moneda,
    TasaDeCambio,
    Transaccion,
)

from operaciones.services import (
    cambiar_estado_transaccion,
    iniciar_facturacion_transaccion,
)

from operaciones.views import stripe_webhook


class IntegracionFacturacionTest(TestCase):

    def setUp(self):

        self.usuario = Usuario.objects.create_user(
            username='usuario_facturacion_test',
            email='facturacion@test.com',
            password='test1234',
        )

        self.cliente = Cliente.objects.create(
            tipo_persona=Cliente.TipoPersona.FISICA,
            nombre_o_denominacion='Cliente Test',
            documento='9876543',
            categoria=Cliente.Categoria.MINORISTA,
            stripe_customer_id='cus_test',
        )

        self.moneda = Moneda.objects.create(
            codigo='EUR',
            nombre='Euro',
        )

        self.tasa = TasaDeCambio.objects.create(
            moneda=self.moneda,
            tasa_base=Decimal('8300.0000'),
            margen_compra=Decimal('0.0000'),
            margen_venta=Decimal('0.0000'),
        )

        self.medio_pago = MedioPago.objects.create(
            usuario=self.usuario,
            cliente=self.cliente,
            tipo='TARJETA',
            nombre_titular='Cliente Test',
            numero_enmascarado='**** 4242',
            stripe_payment_method_id='pm_test',
            activo=True,
        )

        self.transaccion = Transaccion.objects.create(
            usuario=self.usuario,
            cliente=self.cliente,
            moneda=self.moneda,

            tipo=Transaccion.Tipo.COMPRA,
            canal=Transaccion.Canal.WEB,

            monto_pagado=Decimal('2444.00'),
            monto_recibido=Decimal('0.29'),

            tasa_referencia=self.tasa,
            tasa_aplicada=Decimal('8300.0000'),

            categoria_cliente_aplicada=(
                Cliente.Categoria.MINORISTA
            ),

            porcentaje_comision=Decimal('2.00'),
            monto_comision=Decimal('0.0058'),
            moneda_comision='EUR',

            medio_pago=self.medio_pago,

            estado=Transaccion.Estado.PENDIENTE,
            facturada=False,
        )


    @patch(
        'operaciones.services.'
        'iniciar_facturacion_transaccion'
    )
    def test_pagada_dispara_facturacion(
        self,
        mock_iniciar_facturacion,
    ):
        """
        PENDIENTE -> PAGADA debe registrar
        auditoría y disparar facturación
        después del commit.
        """

        with self.captureOnCommitCallbacks(
            execute=True
        ):
            cambiar_estado_transaccion(
                transaccion=self.transaccion,
                nuevo_estado=(
                    Transaccion.Estado.PAGADA
                ),
                usuario=self.usuario,
                motivo='Pago de prueba',
            )

        self.transaccion.refresh_from_db()

        self.assertEqual(
            self.transaccion.estado,
            Transaccion.Estado.PAGADA,
        )

        mock_iniciar_facturacion.assert_called_once_with(
            self.transaccion.id
        )

        self.assertTrue(
            LogTransaccion.objects.filter(
                transaccion=self.transaccion,
                estado_anterior=(
                    Transaccion.Estado.PENDIENTE
                ),
                estado_nuevo=(
                    Transaccion.Estado.PAGADA
                ),
            ).exists()
        )


    @override_settings(
        FACTURACION_EMISION_AUTOMATICA=False
    )
    @patch(
        'facturacion.services.emision.'
        'emitir_factura'
    )
    def test_flag_apagado_no_emite_factura(
        self,
        mock_emitir,
    ):
        """
        Con el flag apagado no se debe
        ejecutar emitir_factura.
        """

        self.transaccion.estado = (
            Transaccion.Estado.PAGADA
        )

        self.transaccion.save(
            update_fields=['estado']
        )

        iniciar_facturacion_transaccion(
            self.transaccion.id
        )

        mock_emitir.assert_not_called()


    @override_settings(
        FACTURACION_EMISION_AUTOMATICA=True
    )
    @patch(
        'facturacion.services.emision.'
        'emitir_factura'
    )
    def test_error_facturacion_no_revierte_pago(
        self,
        mock_emitir,
    ):
        """
        Si Factura Segura falla después
        del pago, PAGADA debe conservarse.
        """

        mock_emitir.side_effect = Exception(
            'Factura Segura no disponible'
        )

        with self.captureOnCommitCallbacks(
            execute=True
        ):
            cambiar_estado_transaccion(
                transaccion=self.transaccion,
                nuevo_estado=(
                    Transaccion.Estado.PAGADA
                ),
                usuario=self.usuario,
                motivo='Pago confirmado',
            )

        self.transaccion.refresh_from_db()

        self.assertEqual(
            self.transaccion.estado,
            Transaccion.Estado.PAGADA,
        )

        mock_emitir.assert_called_once()

        self.assertTrue(
            LogTransaccion.objects.filter(
                transaccion=self.transaccion,
                estado_nuevo=(
                    Transaccion.Estado.PAGADA
                ),
            ).exists()
        )


    def _crear_evento_stripe(self):

        metadata = MagicMock()

        metadata.to_dict.return_value = {
            'transaccion_id': str(
                self.transaccion.id
            )
        }

        payment_intent = SimpleNamespace(
            metadata=metadata,
            customer='cus_test',
            payment_method='pm_test',
        )

        return SimpleNamespace(
            type='payment_intent.succeeded',
            data=SimpleNamespace(
                object=payment_intent
            ),
        )


    def _crear_request_stripe(self):

        return RequestFactory().post(
            '/stripe/webhook/',
            data=b'{}',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='firma-test',
        )


    @override_settings(
        STRIPE_WEBHOOK_SECRET='secreto-test'
    )
    @patch(
        'operaciones.services.'
        'iniciar_facturacion_transaccion'
    )
    @patch(
        'operaciones.views.'
        'stripe.Webhook.construct_event'
    )
    def test_webhook_stripe_repetido_no_duplica(
        self,
        mock_construct_event,
        mock_iniciar_facturacion,
    ):
        """
        Stripe puede reenviar el mismo webhook.

        El primer webhook debe confirmar el pago.
        El segundo no debe crear otro log ni
        disparar otra facturación.
        """

        mock_construct_event.return_value = (
            self._crear_evento_stripe()
        )

        with self.captureOnCommitCallbacks(
            execute=True
        ):
            respuesta_1 = stripe_webhook(
                self._crear_request_stripe()
            )

            respuesta_2 = stripe_webhook(
                self._crear_request_stripe()
            )

        self.transaccion.refresh_from_db()

        self.assertEqual(
            respuesta_1.status_code,
            200,
        )

        self.assertEqual(
            respuesta_2.status_code,
            200,
        )

        self.assertEqual(
            self.transaccion.estado,
            Transaccion.Estado.PAGADA,
        )

        self.assertEqual(
            LogTransaccion.objects.filter(
                transaccion=self.transaccion,
                estado_anterior=(
                    Transaccion.Estado.PENDIENTE
                ),
                estado_nuevo=(
                    Transaccion.Estado.PAGADA
                ),
            ).count(),
            1,
        )

        self.assertEqual(
            mock_iniciar_facturacion.call_count,
            1,
        )