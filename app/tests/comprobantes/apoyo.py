"""Datos de prueba compartidos por los tests de envío de comprobantes (SCRUM-23)."""

from decimal import Decimal

from operaciones.models import TasaDeCambio, Transaccion
from tests.operaciones.datos_historial import HistorialDatosMixin


class ComprobantesDatosMixin(HistorialDatosMixin):
    """Agrega emails, una tasa y transacciones pendientes a los datos del historial.

    - `usuario_a` (asociado a `cliente_a`) tiene email `ana@cliente.test`.
    - El cajero tiene email propio, para comprobar que no recibe el comprobante.
    """

    EMAIL_CLIENTE = 'ana@cliente.test'

    def setUp(self):
        """Carga los datos del historial y los completa para poder pagar transacciones."""
        super().setUp()
        self.usuario_a.email = self.EMAIL_CLIENTE
        self.usuario_a.save(update_fields=['email'])
        self.cajero.email = 'cajero@globalexchange.test'
        self.cajero.save(update_fields=['email'])
        self.tasa = TasaDeCambio.objects.create(
            moneda=self.usd, tasa_base=Decimal('7600'), margen_compra=Decimal('50'), margen_venta=Decimal('50'),
        )

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
