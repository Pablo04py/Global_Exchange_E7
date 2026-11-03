"""Datos de prueba compartidos por los tests de envío de facturas por email (SCRUM-23)."""

from datetime import date
from decimal import Decimal

from facturacion.models import ConfiguracionFacturacion, FacturaElectronica
from operaciones.models import TasaDeCambio, Transaccion
from tests.operaciones.datos_historial import HistorialDatosMixin

CDC_MOCK = '01025957333001003000021722026110312345678901'
KUDE_MOCK = b'%PDF-1.4 KuDE de prueba'


class ComprobantesDatosMixin(HistorialDatosMixin):
    """Agrega emails, una tasa, la configuración fiscal y facturas a los datos del historial.

    - `usuario_a` (asociado a `cliente_a`) tiene email `ana@cliente.test`.
    - El cajero tiene email propio, para comprobar que no recibe la factura.
    """

    EMAIL_CLIENTE = 'ana@cliente.test'

    def setUp(self):
        """Carga los datos del historial y los completa para poder facturar transacciones."""
        super().setUp()
        self.usuario_a.email = self.EMAIL_CLIENTE
        self.usuario_a.save(update_fields=['email'])
        self.cajero.email = 'cajero@globalexchange.test'
        self.cajero.save(update_fields=['email'])
        self.tasa = TasaDeCambio.objects.create(
            moneda=self.usd, tasa_base=Decimal('7600'), margen_compra=Decimal('50'), margen_venta=Decimal('50'),
        )
        self.configuracion = ConfiguracionFacturacion.objects.create(
            nombre_emisor='GLOBAL EXCHANGE', ruc_emisor='2595733', dv_emisor='3',
            timbrado='02595733', fecha_inicio_timbrado=date(2025, 3, 27),
            establecimiento='001', punto_expedicion='003', direccion='San Lorenzo',
            email='bgx.globalexchange@gmail.com', activa=True,
        )
        self._siguiente_numero = 217

    def crear_pendiente(self, **campos):
        """Crea una compra de 100 USD de `cliente_a` en estado `PENDIENTE`.

        Args:
            **campos: Campos de `Transaccion` que reemplazan a los valores por defecto.

        Returns:
            Transaccion: La transacción creada.
        """
        valores = {
            'estado': Transaccion.Estado.PENDIENTE,
            'tasa_referencia': self.tasa,
            'categoria_cliente_aplicada': self.cliente_a.categoria,
            'porcentaje_comision': Decimal('1.00'),
            'monto_comision': Decimal('7650.0000'),
            'moneda_comision': 'PYG',
        }
        valores.update(campos)
        return self.crear_transaccion(**valores)

    def crear_factura(self, transaccion=None, estado=FacturaElectronica.Estado.EMITIDA):
        """Crea la factura electrónica de una transacción pagada.

        Fuera de `captureOnCommitCallbacks` la señal no llega a encolar el
        envío, porque en los tests los callbacks `on_commit` se descartan.

        Args:
            transaccion: Transacción facturada (por defecto, una nueva compra pagada).
            estado: Estado de la factura (por defecto `EMITIDA`).

        Returns:
            FacturaElectronica: La factura creada.
        """
        transaccion = transaccion or self.crear_pendiente(estado=Transaccion.Estado.PAGADA)
        numero = self._siguiente_numero
        self._siguiente_numero += 1
        return FacturaElectronica.objects.create(
            transaccion=transaccion, configuracion=self.configuracion,
            numero_documento=f'{numero:07d}', cdc=f'{CDC_MOCK[:-3]}{numero:03d}', estado=estado,
        )

    def aprobar(self, factura):
        """Marca la factura `APROBADA` ejecutando los callbacks `on_commit` como si hubiera commit."""
        with self.captureOnCommitCallbacks(execute=True):
            factura.estado = FacturaElectronica.Estado.APROBADA
            factura.save()
        return factura
