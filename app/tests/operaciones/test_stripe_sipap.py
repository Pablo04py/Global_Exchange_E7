"""
Pruebas de integración para confirmación de pagos con Stripe y SIPAP.

Stripe está completamente mockeado:
- No realiza pagos reales.
- No llama a la API real de Stripe.
- No necesita Stripe CLI.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from clientes.models import Cliente, UsuarioCliente
from mpagos.models import MedioPago
from operaciones.models import (
    LogTransaccion,
    Moneda,
    TasaDeCambio,
    Transaccion,
)
from operaciones.services import cambiar_estado_transaccion


Usuario = get_user_model()


class AttrDict(dict):
    """
    Diccionario que imita parcialmente un StripeObject.

    Permite:
    - acceso mediante []
    - acceso mediante atributos
    - uso de .to_dict()
    """

    def __getattr__(self, nombre):
        try:
            return self[nombre]
        except KeyError as exc:
            raise AttributeError(nombre) from exc

    def to_dict(self):
        return dict(self)


@override_settings(
    STRIPE_SECRET_KEY="sk_test_unit_tests",
    STRIPE_PUBLISHABLE_KEY="pk_test_unit_tests",
    STRIPE_WEBHOOK_SECRET="whsec_unit_tests",
    STRIPE_CURRENCY="pyg",
)
class PagosBaseTestCase(TestCase):
    """
    Datos comunes para las pruebas de Stripe y SIPAP.
    """

    def setUp(self):

        # ---------------------------------------------------------
        # USUARIO
        # ---------------------------------------------------------

        self.usuario = Usuario.objects.create_user(
            username="usuario_pago",
            email="usuario@globalexchange.test",
            password="password123",
        )

        # ---------------------------------------------------------
        # CLIENTE
        # ---------------------------------------------------------

        self.cliente_ge = Cliente.objects.create(
            tipo_persona=Cliente.TipoPersona.FISICA,
            nombre_o_denominacion="Cliente Pagos",
            documento="1234567",
            categoria=Cliente.Categoria.MINORISTA,
        )

        # Customer falso de Stripe
        self.cliente_ge.stripe_customer_id = (
            "cus_test_global_exchange"
        )

        self.cliente_ge.save(
            update_fields=[
                "stripe_customer_id"
            ]
        )

        UsuarioCliente.objects.create(
            usuario=self.usuario,
            cliente=self.cliente_ge,
        )

        # ---------------------------------------------------------
        # MONEDA Y TASA
        # ---------------------------------------------------------

        self.moneda = Moneda.objects.create(
            codigo="USD",
            nombre="Dólar estadounidense",
        )

        self.tasa = TasaDeCambio.objects.create(
            moneda=self.moneda,
            tasa_base=Decimal("7500.0000"),
            margen_compra=Decimal("50.0000"),
            margen_venta=Decimal("50.0000"),
        )

        # ---------------------------------------------------------
        # TARJETA STRIPE
        # ---------------------------------------------------------

        self.tarjeta = MedioPago.objects.create(
            usuario=self.usuario,
            cliente=self.cliente_ge,
            tipo="TARJETA",
            nombre_titular="Cliente Pagos",
            numero_enmascarado="**** 4242",

            stripe_payment_method_id="pm_test_4242",

            marca_tarjeta="visa",
            exp_mes=12,
            exp_anio=2030,

            activo=True,
        )

        # ---------------------------------------------------------
        # SIPAP
        # ---------------------------------------------------------

        self.sipap = MedioPago.objects.create(
            usuario=self.usuario,
            cliente=self.cliente_ge,
            tipo="SIPAP",
            nombre_titular="Cliente Pagos",
            banco_emisor="Banco Test",
            numero_enmascarado="CTA-TEST",
            activo=True,
        )

        # ---------------------------------------------------------
        # LOGIN
        # ---------------------------------------------------------

        self.client.force_login(
            self.usuario
        )

        # Cliente activo en sesión
        session = self.client.session

        session[
            "ge_active_client"
        ] = str(
            self.cliente_ge.id
        )

        session.save()

    # =============================================================
    # CREAR TRANSACCIÓN DE PRUEBA
    # =============================================================

    def crear_transaccion(
        self,
        medio_pago,
        estado=Transaccion.Estado.PENDIENTE,
    ):

        return Transaccion.objects.create(

            cliente=self.cliente_ge,

            usuario=self.usuario,

            tipo=Transaccion.Tipo.COMPRA,

            moneda=self.moneda,

            medio_pago=medio_pago,

            monto_pagado=Decimal(
                "780000.00"
            ),

            monto_recibido=Decimal(
                "103.31"
            ),

            tasa_referencia=self.tasa,

            tasa_aplicada=Decimal(
                "7550.0000"
            ),

            categoria_cliente_aplicada=(
                self.cliente_ge.categoria
            ),

            porcentaje_comision=Decimal(
                "2.00"
            ),

            monto_comision=Decimal(
                "2.0662"
            ),

            moneda_comision="USD",

            estado=estado,
        )

    # =============================================================
    # EVENTO STRIPE FALSO
    # =============================================================

    def evento_payment_intent_succeeded(
        self,
        transaccion,
    ):
        """
        Simula el PaymentIntent que Stripe incluye
        dentro de payment_intent.succeeded.
        """

        metadata = AttrDict(

            transaccion_id=str(
                transaccion.id
            ),

            cliente_id=str(
                transaccion.cliente_id
            ),
        )

        payment_intent = AttrDict(

            id="pi_test_confirmado",

            status="succeeded",

            # Tu webhook consulta este campo
            customer=(
                self.cliente_ge
                .stripe_customer_id
            ),

            # Lo agregamos también para que el mock
            # represente correctamente la tarjeta usada
            payment_method=(
                self.tarjeta
                .stripe_payment_method_id
            ),

            metadata=metadata,
        )

        evento = AttrDict(

            type=(
                "payment_intent.succeeded"
            ),

            data=AttrDict(
                object=payment_intent
            ),
        )

        return evento

    # =============================================================
    # ENVIAR WEBHOOK FALSO
    # =============================================================

    def enviar_webhook_stripe(
        self,
        evento,
    ):

        with patch(
            (
                "operaciones.views."
                "stripe.Webhook.construct_event"
            ),
            return_value=evento,
        ):

            return self.client.post(

                reverse(
                    "stripe_webhook"
                ),

                data=b"{}",

                content_type=(
                    "application/json"
                ),

                HTTP_STRIPE_SIGNATURE=(
                    "firma-test"
                ),
            )


# =================================================================
# TESTS STRIPE
# =================================================================


class StripePagoTestCase(PagosBaseTestCase):

    # =============================================================
    # CREACIÓN DEL PAYMENT INTENT
    # =============================================================
    @patch("operaciones.pagos." "stripe_service." "stripe.PaymentIntent.create")
    @patch("operaciones.pagos." "stripe_service." "stripe.PaymentMethod.retrieve")
    def test_iniciar_pago_crea_payment_intent_y_sigue_pendiente(self, mock_payment_method_retrieve,mock_payment_intent_create,):
        """
        Al iniciar un pago con Stripe:

        - Se verifica que el PaymentMethod pertenezca
          al Customer del cliente.
        - Se crea un PaymentIntent.
        - Se devuelve el client_secret.
        - La transacción continúa PENDIENTE.
        - Todavía no se genera LogTransaccion.
        """

        # ---------------------------------------------------------
        # TRANSACCIÓN
        # ---------------------------------------------------------

        transaccion = self.crear_transaccion(
            self.tarjeta
        )

        # ---------------------------------------------------------
        # PAYMENT METHOD FALSO
        # ---------------------------------------------------------
        # El servicio primero consulta Stripe para verificar
        # que la tarjeta pertenece al Customer correcto.

        payment_method = MagicMock()

        payment_method.id = (
            self.tarjeta.stripe_payment_method_id
        )

        payment_method.customer = (
            self.cliente_ge.stripe_customer_id
        )

        mock_payment_method_retrieve.return_value = (
            payment_method
        )

        # ---------------------------------------------------------
        # PAYMENT INTENT FALSO
        # ---------------------------------------------------------

        payment_intent = MagicMock()

        payment_intent.id = (
            "pi_test_123"
        )

        payment_intent.client_secret = (
            "pi_test_123_secret_456"
        )

        payment_intent.status = (
            "requires_confirmation"
        )

        mock_payment_intent_create.return_value = (
            payment_intent
        )

        # ---------------------------------------------------------
        # EJECUTAR ENDPOINT
        # ---------------------------------------------------------

        response = self.client.post(

            reverse(
                "iniciar_pago_stripe",

                kwargs={
                    "transaccion_id":
                        transaccion.id
                },
            )
        )

        # ---------------------------------------------------------
        # RESPUESTA HTTP
        # ---------------------------------------------------------

        self.assertEqual(
            response.status_code,
            200,
        )

        datos = response.json()

        self.assertEqual(
            datos["client_secret"],
            "pi_test_123_secret_456",
        )

        # ---------------------------------------------------------
        # STRIPE VERIFICÓ EL PAYMENT METHOD
        # ---------------------------------------------------------

        mock_payment_method_retrieve.assert_called_once_with(
            self.tarjeta.stripe_payment_method_id
        )

        # ---------------------------------------------------------
        # STRIPE CREÓ EL PAYMENT INTENT
        # ---------------------------------------------------------

        mock_payment_intent_create.assert_called_once()

        kwargs = (
            mock_payment_intent_create
            .call_args
            .kwargs
        )

        # Customer correcto
        self.assertEqual(
            kwargs.get("customer"),
            self.cliente_ge.stripe_customer_id,
        )

        # Tarjeta correcta
        self.assertEqual(
            kwargs.get("payment_method"),
            self.tarjeta.stripe_payment_method_id,
        )

        # Moneda
        self.assertEqual(
            kwargs.get("currency"),
            "pyg",
        )

        # Metadata
        metadata = kwargs.get(
            "metadata",
            {},
        )

        self.assertEqual(
            str(
                metadata.get(
                    "transaccion_id"
                )
            ),
            str(
                transaccion.id
            ),
        )

        self.assertEqual(
            str(
                metadata.get(
                    "cliente_id"
                )
            ),
            str(
                self.cliente_ge.id
            ),
        )

        self.assertEqual(
            str(
                metadata.get(
                    "medio_pago_id"
                )
            ),
            str(
                self.tarjeta.id
            ),
        )

        # ---------------------------------------------------------
        # CVC DEBE SOLICITARSE NUEVAMENTE
        # ---------------------------------------------------------

        opciones = kwargs.get(
            "payment_method_options",
            {},
        )

        self.assertTrue(
            opciones
            .get(
                "card",
                {},
            )
            .get(
                "require_cvc_recollection"
            )
        )

        # ---------------------------------------------------------
        # LA TRANSACCIÓN TODAVÍA NO ESTÁ PAGADA
        # ---------------------------------------------------------

        transaccion.refresh_from_db()

        self.assertEqual(
            transaccion.estado,
            Transaccion.Estado.PENDIENTE,
        )

        # El Log solamente debe aparecer cuando
        # Stripe confirme posteriormente mediante webhook.

        self.assertFalse(
            LogTransaccion.objects.filter(
                transaccion=transaccion
            ).exists()
        )

    # =============================================================
    # SOLO POST
    # =============================================================

    def test_iniciar_pago_stripe_solo_acepta_post(
        self
    ):

        transaccion = (
            self.crear_transaccion(
                self.tarjeta
            )
        )

        response = self.client.get(

            reverse(
                "iniciar_pago_stripe",

                kwargs={
                    "transaccion_id":
                        transaccion.id
                },
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    # =============================================================
    # WEBHOOK EXITOSO
    # =============================================================

    def test_webhook_succeeded_marca_pagada_y_crea_log(
        self
    ):

        transaccion = (
            self.crear_transaccion(
                self.tarjeta
            )
        )

        evento = (
            self.evento_payment_intent_succeeded(
                transaccion
            )
        )

        response = (
            self.enviar_webhook_stripe(
                evento
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        transaccion.refresh_from_db()

        # ---------------------------------------------------------
        # ESTADO
        # ---------------------------------------------------------

        self.assertEqual(
            transaccion.estado,
            Transaccion.Estado.PAGADA,
        )

        # ---------------------------------------------------------
        # LOG
        # ---------------------------------------------------------

        logs = (
            LogTransaccion.objects.filter(
                transaccion=transaccion
            )
        )

        self.assertEqual(
            logs.count(),
            1,
        )

        log = logs.get()

        self.assertEqual(
            log.estado_anterior,
            Transaccion.Estado.PENDIENTE,
        )

        self.assertEqual(
            log.estado_nuevo,
            Transaccion.Estado.PAGADA,
        )

        self.assertEqual(
            log.usuario,
            self.usuario,
        )

        self.assertIn(
            "STRIPE",
            (
                log.motivo
                or ""
            ).upper(),
        )

    # =============================================================
    # WEBHOOK REPETIDO
    # =============================================================

    def test_webhook_repetido_no_duplica_log(
        self
    ):
        """
        Stripe puede reenviar webhooks.

        Una segunda recepción del mismo evento
        no debe volver a cambiar el estado.
        """

        transaccion = (
            self.crear_transaccion(
                self.tarjeta
            )
        )

        evento = (
            self.evento_payment_intent_succeeded(
                transaccion
            )
        )

        primera = (
            self.enviar_webhook_stripe(
                evento
            )
        )

        segunda = (
            self.enviar_webhook_stripe(
                evento
            )
        )

        self.assertEqual(
            primera.status_code,
            200,
        )

        self.assertEqual(
            segunda.status_code,
            200,
        )

        transaccion.refresh_from_db()

        self.assertEqual(
            transaccion.estado,
            Transaccion.Estado.PAGADA,
        )

        self.assertEqual(

            LogTransaccion.objects.filter(
                transaccion=transaccion
            ).count(),

            1,
        )

    # =============================================================
    # FIRMA INVÁLIDA
    # =============================================================

    def test_webhook_firma_invalida_no_cambia_estado(
        self
    ):

        transaccion = (
            self.crear_transaccion(
                self.tarjeta
            )
        )

        with patch(

            (
                "operaciones.views."
                "stripe.Webhook."
                "construct_event"
            ),

            side_effect=ValueError(
                "firma inválida"
            ),
        ):

            response = self.client.post(

                reverse(
                    "stripe_webhook"
                ),

                data=b"{}",

                content_type=(
                    "application/json"
                ),

                HTTP_STRIPE_SIGNATURE=(
                    "firma-invalida"
                ),
            )

        self.assertEqual(
            response.status_code,
            400,
        )

        transaccion.refresh_from_db()

        self.assertEqual(
            transaccion.estado,
            Transaccion.Estado.PENDIENTE,
        )

        self.assertFalse(

            LogTransaccion.objects.filter(
                transaccion=transaccion
            ).exists()
        )

    # =============================================================
    # POLLING - PENDIENTE
    # =============================================================

    def test_estado_pago_stripe_false_si_pendiente(
        self
    ):

        transaccion = (
            self.crear_transaccion(
                self.tarjeta
            )
        )

        response = self.client.get(

            reverse(
                "estado_pago_stripe",

                kwargs={
                    "transaccion_id":
                        transaccion.id
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            response.json()[
                "pagada"
            ]
        )

    # =============================================================
    # POLLING - PAGADA
    # =============================================================

    def test_estado_pago_stripe_true_si_pagada(
        self
    ):

        transaccion = (
            self.crear_transaccion(
                self.tarjeta
            )
        )

        cambiar_estado_transaccion(

            transaccion=transaccion,

            nuevo_estado=(
                Transaccion
                .Estado
                .PAGADA
            ),

            usuario=self.usuario,

            motivo=(
                "Pago confirmado "
                "mediante Stripe Sandbox."
            ),
        )

        response = self.client.get(

            reverse(
                "estado_pago_stripe",

                kwargs={
                    "transaccion_id":
                        transaccion.id
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.json()[
                "pagada"
            ]
        )


# =================================================================
# TESTS SIPAP
# =================================================================


class SipapPagoTestCase(
    PagosBaseTestCase
):

    # =============================================================
    # CONFIRMACIÓN EXITOSA
    # =============================================================

    def test_confirmar_sipap_marca_pagada_y_crea_log(
        self
    ):

        transaccion = (
            self.crear_transaccion(
                self.sipap
            )
        )

        response = self.client.post(

            reverse(
                "confirmar_pago_sipap",

                kwargs={
                    "transaccion_id":
                        transaccion.id
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        transaccion.refresh_from_db()

        self.assertEqual(
            transaccion.estado,
            Transaccion.Estado.PAGADA,
        )

        logs = (
            LogTransaccion.objects.filter(
                transaccion=transaccion
            )
        )

        self.assertEqual(
            logs.count(),
            1,
        )

        log = logs.get()

        self.assertEqual(
            log.estado_anterior,
            Transaccion.Estado.PENDIENTE,
        )

        self.assertEqual(
            log.estado_nuevo,
            Transaccion.Estado.PAGADA,
        )

        self.assertEqual(
            log.usuario,
            self.usuario,
        )

        self.assertIn(
            "SIPAP",
            (
                log.motivo
                or ""
            ).upper(),
        )

    # =============================================================
    # SOLO POST
    # =============================================================

    def test_confirmar_sipap_solo_acepta_post(
        self
    ):

        transaccion = (
            self.crear_transaccion(
                self.sipap
            )
        )

        response = self.client.get(

            reverse(
                "confirmar_pago_sipap",

                kwargs={
                    "transaccion_id":
                        transaccion.id
                },
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        transaccion.refresh_from_db()

        self.assertEqual(
            transaccion.estado,
            Transaccion.Estado.PENDIENTE,
        )

    # =============================================================
    # NO PERMITIR TARJETA EN SIPAP
    # =============================================================

    def test_sipap_no_confirma_una_transaccion_de_tarjeta(
        self
    ):

        transaccion = (
            self.crear_transaccion(
                self.tarjeta
            )
        )

        response = self.client.post(

            reverse(
                "confirmar_pago_sipap",

                kwargs={
                    "transaccion_id":
                        transaccion.id
                },
            )
        )

        self.assertIn(
            response.status_code,
            (
                302,
                400,
            ),
        )

        transaccion.refresh_from_db()

        self.assertEqual(
            transaccion.estado,
            Transaccion.Estado.PENDIENTE,
        )

        self.assertFalse(

            LogTransaccion.objects.filter(
                transaccion=transaccion
            ).exists()
        )

    # =============================================================
    # DOBLE CONFIRMACIÓN
    # =============================================================

    def test_confirmar_sipap_dos_veces_no_duplica_log(
        self
    ):

        transaccion = (
            self.crear_transaccion(
                self.sipap
            )
        )

        url = reverse(

            "confirmar_pago_sipap",

            kwargs={
                "transaccion_id":
                    transaccion.id
            },
        )

        primera = self.client.post(
            url
        )

        segunda = self.client.post(
            url
        )

        self.assertIn(
            primera.status_code,
            (
                200,
                302,
            ),
        )

        self.assertIn(
            segunda.status_code,
            (
                200,
                302,
                400,
            ),
        )

        transaccion.refresh_from_db()

        self.assertEqual(
            transaccion.estado,
            Transaccion.Estado.PAGADA,
        )

        self.assertEqual(

            LogTransaccion.objects.filter(
                transaccion=transaccion
            ).count(),

            1,
        )

    # =============================================================
    # AISLAMIENTO ENTRE CLIENTES
    # =============================================================

    def test_usuario_no_confirma_sipap_de_otro_cliente(
        self
    ):

        otro_usuario = (
            Usuario.objects.create_user(

                username=(
                    "otro_usuario"
                ),

                email=(
                    "otro@globalexchange.test"
                ),

                password=(
                    "password123"
                ),
            )
        )

        otro_cliente = (
            Cliente.objects.create(

                tipo_persona=(
                    Cliente
                    .TipoPersona
                    .FISICA
                ),

                nombre_o_denominacion=(
                    "Otro Cliente"
                ),

                documento=(
                    "7654321"
                ),

                categoria=(
                    Cliente
                    .Categoria
                    .MINORISTA
                ),
            )
        )

        UsuarioCliente.objects.create(

            usuario=otro_usuario,

            cliente=otro_cliente,
        )

        otro_sipap = (
            MedioPago.objects.create(

                usuario=otro_usuario,

                cliente=otro_cliente,

                tipo="SIPAP",

                nombre_titular=(
                    "Otro Cliente"
                ),

                banco_emisor=(
                    "Banco Ajeno"
                ),

                numero_enmascarado=(
                    "CTA-AJENA"
                ),

                activo=True,
            )
        )

        transaccion_ajena = (
            Transaccion.objects.create(

                cliente=otro_cliente,

                usuario=otro_usuario,

                tipo=(
                    Transaccion
                    .Tipo
                    .COMPRA
                ),

                moneda=self.moneda,

                medio_pago=(
                    otro_sipap
                ),

                monto_pagado=Decimal(
                    "500000.00"
                ),

                monto_recibido=Decimal(
                    "66.22"
                ),

                tasa_referencia=(
                    self.tasa
                ),

                tasa_aplicada=Decimal(
                    "7550.0000"
                ),

                categoria_cliente_aplicada=(
                    otro_cliente.categoria
                ),

                porcentaje_comision=Decimal(
                    "2.00"
                ),

                monto_comision=Decimal(
                    "1.3244"
                ),

                moneda_comision="USD",

                estado=(
                    Transaccion
                    .Estado
                    .PENDIENTE
                ),
            )
        )

        response = self.client.post(

            reverse(

                "confirmar_pago_sipap",

                kwargs={
                    "transaccion_id":
                        transaccion_ajena.id
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        transaccion_ajena.refresh_from_db()

        self.assertEqual(

            transaccion_ajena.estado,

            Transaccion
            .Estado
            .PENDIENTE,
        )

        self.assertFalse(

            LogTransaccion.objects.filter(
                transaccion=(
                    transaccion_ajena
                )
            ).exists()
        )
