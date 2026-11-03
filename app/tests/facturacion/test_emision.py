from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from usuarios.models import Usuario
from clientes.models import Cliente
from mpagos.models import MedioPago

from operaciones.models import (
    Moneda,
    TasaDeCambio,
    Transaccion,
)

from facturacion.models import (
    ConfiguracionFacturacion,
    FacturaElectronica,
)

from facturacion.services.emision import (
    emitir_factura,
    sincronizar_estado_sifen,
    ErrorEmisionFactura,
)

from facturacion.services.factura_segura import (
    FacturaSeguraError,
)


CDC_MOCK = (
    '12345678901234567890123456789012345678901234'
)


class FacturacionBaseTest(TestCase):

    def setUp(self):

        self.usuario = Usuario.objects.create_user(
            username='usuario_test',
            email='usuario@test.com',
            password='test1234',
        )

        self.cliente = Cliente.objects.create(
            tipo_persona=Cliente.TipoPersona.FISICA,
            nombre_o_denominacion='Cliente Test',
            documento='1234567',
            categoria=Cliente.Categoria.MINORISTA,
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
            tipo='EFECTIVO',
            nombre_titular='Efectivo en caja',
            numero_enmascarado='CAJA',
            activo=True,
        )

        self.transaccion = Transaccion.objects.create(
            usuario=self.usuario,
            cliente=self.cliente,
            moneda=self.moneda,
            tipo=Transaccion.Tipo.COMPRA,
            canal=Transaccion.Canal.CAJA,

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

            estado=Transaccion.Estado.PAGADA,
            facturada=False,
        )

        self.configuracion = (
            ConfiguracionFacturacion.objects.create(
                nombre_emisor='GLOBAL EXCHANGE',

                ruc_emisor='2595733',
                dv_emisor='3',
                tipo_contribuyente='1',

                timbrado='02595733',
                fecha_inicio_timbrado=date(
                    2025,
                    3,
                    27,
                ),

                establecimiento='001',
                punto_expedicion='003',

                direccion='San Lorenzo',
                numero_casa='0',

                departamento_codigo='12',
                departamento_descripcion='CENTRAL',

                ciudad_codigo='6010',
                ciudad_descripcion='SAN LORENZO',

                telefono='(021)5887000',

                email=(
                    'bgx.globalexchange@gmail.com'
                ),

                actividades_economicas=[
                    {
                        'cActEco': '62010',
                        'dDesActEco': (
                            'Actividades de '
                            'programación informática'
                        ),
                    },
                    {
                        'cActEco': '74909',
                        'dDesActEco': (
                            'Otras actividades '
                            'profesionales, científicas '
                            'y técnicas n.c.p.'
                        ),
                    },
                ],

                siguiente_numero_documento=217,

                activa=True,
            )
        )

    def respuesta_calculo(self):

        return {
            'code': 0,
            'description': 'OK',
            'operation_info': {
                'id': 'mock-calculo-001'
            },
            'results': [
                {
                    'DE': {
                        'dNumDoc': '0000217'
                    }
                }
            ],
        }

    def respuesta_generacion(self):

        return {
            'code': 0,
            'description': 'OK',
            'operation_info': {
                'id': 'mock-generacion-001'
            },
            'results': [
                {
                    'CDC': CDC_MOCK
                }
            ],
        }


class EmisionFacturaTest(FacturacionBaseTest):

    @patch(
        'facturacion.services.emision.'
        'construir_json_resumido'
    )
    @patch(
        'facturacion.services.emision.'
        'FacturaSeguraService.generar_de'
    )
    @patch(
        'facturacion.services.emision.'
        'FacturaSeguraService.calcular_de'
    )
    def test_emision_exitosa(
        self,
        mock_calcular,
        mock_generar,
        mock_builder,
    ):

        mock_builder.return_value = {
            'dNumDoc': '0000217'
        }

        mock_calcular.return_value = (
            self.respuesta_calculo()
        )

        mock_generar.return_value = (
            self.respuesta_generacion()
        )

        factura = emitir_factura(
            self.transaccion
        )

        self.transaccion.refresh_from_db()

        self.configuracion.refresh_from_db()

        self.assertEqual(
            factura.numero_documento,
            '0000217',
        )

        self.assertEqual(
            factura.estado,
            FacturaElectronica.Estado.EMITIDA,
        )

        self.assertEqual(
            factura.cdc,
            CDC_MOCK,
        )

        self.assertTrue(
            self.transaccion.facturada
        )

        self.assertEqual(
            self.configuracion
            .siguiente_numero_documento,
            218,
        )

        mock_calcular.assert_called_once()

        mock_generar.assert_called_once()


    @patch(
        'facturacion.services.emision.'
        'construir_json_resumido'
    )
    @patch(
        'facturacion.services.emision.'
        'FacturaSeguraService.generar_de'
    )
    @patch(
        'facturacion.services.emision.'
        'FacturaSeguraService.calcular_de'
    )
    def test_emision_es_idempotente(
        self,
        mock_calcular,
        mock_generar,
        mock_builder,
    ):

        mock_builder.return_value = {
            'dNumDoc': '0000217'
        }

        mock_calcular.return_value = (
            self.respuesta_calculo()
        )

        mock_generar.return_value = (
            self.respuesta_generacion()
        )

        factura_1 = emitir_factura(
            self.transaccion
        )

        factura_2 = emitir_factura(
            self.transaccion
        )

        self.configuracion.refresh_from_db()

        self.assertEqual(
            factura_1.id,
            factura_2.id,
        )

        self.assertEqual(
            FacturaElectronica.objects.filter(
                transaccion=self.transaccion
            ).count(),
            1,
        )

        self.assertEqual(
            mock_calcular.call_count,
            1,
        )

        self.assertEqual(
            mock_generar.call_count,
            1,
        )

        self.assertEqual(
            self.configuracion
            .siguiente_numero_documento,
            218,
        )


    @patch(
        'facturacion.services.emision.'
        'construir_json_resumido'
    )
    @patch(
        'facturacion.services.emision.'
        'FacturaSeguraService.generar_de'
    )
    @patch(
        'facturacion.services.emision.'
        'FacturaSeguraService.calcular_de'
    )
    def test_error_en_generacion(
        self,
        mock_calcular,
        mock_generar,
        mock_builder,
    ):

        mock_builder.return_value = {
            'dNumDoc': '0000217'
        }

        mock_calcular.return_value = (
            self.respuesta_calculo()
        )

        mock_generar.side_effect = (
            FacturaSeguraError(
                'Error simulado'
            )
        )

        with self.assertRaises(
            ErrorEmisionFactura
        ):
            emitir_factura(
                self.transaccion
            )

        factura = (
            FacturaElectronica.objects.get(
                transaccion=self.transaccion
            )
        )

        self.transaccion.refresh_from_db()

        self.configuracion.refresh_from_db()

        self.assertEqual(
            factura.estado,
            FacturaElectronica.Estado.ERROR,
        )

        self.assertEqual(
            self.transaccion.estado,
            Transaccion.Estado.PAGADA,
        )

        self.assertFalse(
            self.transaccion.facturada
        )

        self.assertEqual(
            self.configuracion
            .siguiente_numero_documento,
            217,
        )

class EstadoSifenTest(FacturacionBaseTest):

    def setUp(self):

        super().setUp()

        self.factura = (
            FacturaElectronica.objects.create(
                transaccion=self.transaccion,
                configuracion=self.configuracion,

                numero_documento='0000217',

                cdc=CDC_MOCK,

                estado=(
                    FacturaElectronica.Estado.EMITIDA
                ),
            )
        )

    def respuesta_sifen(
        self,
        estado,
        descripcion='',
        error='',
    ):

        return {
            'code': 0,
            'description': 'OK',

            'operation_info': {
                'id': 'mock-sifen'
            },

            'results': [
                {
                    'estado_sifen': estado,
                    'desc_sifen': descripcion,
                    'error_sifen': error,
                    'fch_sifen': (
                        '2026-10-30 16:00:00'
                    ),
                }
            ],
        }


    @patch(
        'facturacion.services.emision.'
        'FacturaSeguraService.get_estado_sifen'
    )
    def test_sifen_aprobado(
        self,
        mock_estado,
    ):

        mock_estado.return_value = (
            self.respuesta_sifen(
                'Aprobado',
                '0260 - Aprobado',
            )
        )

        factura = sincronizar_estado_sifen(
            self.factura
        )

        self.assertEqual(
            factura.estado,
            FacturaElectronica.Estado.APROBADA,
        )

        self.assertIsNotNone(
            factura.fecha_aprobacion
        )


    @patch(
        'facturacion.services.emision.'
        'FacturaSeguraService.get_estado_sifen'
    )
    def test_sifen_rechazado(
        self,
        mock_estado,
    ):

        mock_estado.return_value = (
            self.respuesta_sifen(
                'Rechazado',
                'Documento rechazado',
                'Datos inválidos',
            )
        )

        factura = sincronizar_estado_sifen(
            self.factura
        )

        self.assertEqual(
            factura.estado,
            FacturaElectronica.Estado.RECHAZADA,
        )

        self.assertIn(
            'Datos inválidos',
            factura.descripcion_respuesta,
        )


    @patch(
        'facturacion.services.emision.'
        'FacturaSeguraService.get_estado_sifen'
    )
    def test_sifen_pendiente(
        self,
        mock_estado,
    ):

        for estado in (
            'SOL.APROBACION',
            'ENVIADO_A_SIFEN',
        ):

            self.factura.estado = (
                FacturaElectronica.Estado.EMITIDA
            )

            self.factura.save(
                update_fields=['estado']
            )

            mock_estado.return_value = (
                self.respuesta_sifen(
                    estado,
                    'Pendiente',
                )
            )

            factura = sincronizar_estado_sifen(
                self.factura
            )

            self.assertEqual(
                factura.estado,
                FacturaElectronica.Estado.EMITIDA,
            )


    @patch(
        'facturacion.services.emision.'
        'FacturaSeguraService.get_estado_sifen'
    )
    def test_sifen_error(
        self,
        mock_estado,
    ):

        estados_error = (
            'ERROR_SIFEN',
            'ERROR_ENVIO_LOTE',
            'REINTENTAR_LOTE',
            'ERROR_CONSULTA_LOTE',
        )

        for estado in estados_error:

            self.factura.estado = (
                FacturaElectronica.Estado.EMITIDA
            )

            self.factura.save(
                update_fields=['estado']
            )

            mock_estado.return_value = (
                self.respuesta_sifen(
                    estado,
                    'Error SIFEN',
                    'Error de procesamiento',
                )
            )

            factura = sincronizar_estado_sifen(
                self.factura
            )

            self.assertEqual(
                factura.estado,
                FacturaElectronica.Estado.ERROR,
            )