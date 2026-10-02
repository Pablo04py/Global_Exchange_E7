"""Modelos de la aplicación operaciones (monedas, tasas de cambio y transacciones)."""

from django.db import models
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from clientes.models import Cliente


class Moneda(models.Model):
    """Moneda extranjera operada por la casa de cambios.

    Attributes:
        id: Identificador UUID, no editable.
        codigo: Código ISO 4217 de 3 letras (ej. `USD`), único.
        nombre: Nombre de la moneda.
        habilitada: Si la moneda se muestra y puede operarse.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=3, unique=True)  # ISO 4217
    nombre = models.CharField(max_length=50)
    habilitada = models.BooleanField(default=True)

    def __str__(self):
        """Devuelve el código ISO de la moneda."""
        return self.codigo

    class Meta:
        """Nombres legibles y orden alfabético por código."""
        verbose_name = "Moneda"
        verbose_name_plural = "Monedas"
        ordering = ['codigo']


class TasaDeCambio(models.Model):
    """Tasa de cambio de una moneda respecto al guaraní (PYG).

    Cada registro es histórico: la tasa vigente es la más reciente
    (ordenadas por `fecha_vigencia` descendente).

    Attributes:
        moneda: Moneda a la que pertenece la tasa.
        tasa_base: Valor de referencia en PYG.
        margen_compra: Monto que se resta a la base para el precio de compra.
        margen_venta: Monto que se suma a la base para el precio de venta.
        fecha_vigencia: Fecha y hora de registro de la tasa.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    moneda = models.ForeignKey(Moneda, on_delete=models.CASCADE, related_name='tasas')
    tasa_base = models.DecimalField(max_digits=12, decimal_places=4)
    margen_compra = models.DecimalField(max_digits=12, decimal_places=4)
    margen_venta = models.DecimalField(max_digits=12, decimal_places=4)
    fecha_vigencia = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Nombres legibles y orden de más reciente a más antigua."""
        verbose_name = "Tasa de Cambio"
        verbose_name_plural = "Tasas de Cambio"
        ordering = ['-fecha_vigencia']

    def __str__(self):
        """Devuelve `MONEDA @ dd/mm/aaaa hh:mm`."""
        return f"{self.moneda.codigo} @ {self.fecha_vigencia:%d/%m/%Y %H:%M}"

    def calcular_precio_compra(self):
        """Calcula el precio al que la casa compra la moneda.

        Returns:
            Decimal: `tasa_base - margen_compra`.
        """
        return self.tasa_base - self.margen_compra

    def calcular_precio_venta(self):
        """Calcula el precio al que la casa vende la moneda.

        Returns:
            Decimal: `tasa_base + margen_venta`.
        """
        return self.tasa_base + self.margen_venta

class ConfiguracionComision(models.Model):
    """Comision vigente segun la categoria del cliente"""

    id=models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    categoria = models.CharField(max_length=20, choices=Cliente.Categoria.choices, unique=True)
    porcentaje = models.DecimalField(max_digits=5,decimal_places=2,validators=[MinValueValidator(0),MaxValueValidator(100)])
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_categoria_display()} - {self.porcentaje}%"


class Transaccion(models.Model):
    """Operación de compra o venta de divisas realizada en nombre de un cliente.

    Un cliente puede tener varios usuarios asociados que operan en su nombre
    y un usuario puede operar para varios clientes: `cliente` indica a nombre
    de quién se hizo la operación y `usuario`, quién la realizó.

    El tipo se interpreta desde el punto de vista del cliente:

    - `COMPRA`: el cliente paga guaraníes (PYG) y recibe la divisa.
    - `VENTA`: el cliente paga la divisa y recibe guaraníes (PYG).

    Los registros son de auditoría: las claves foráneas usan `PROTECT` para
    que el historial no se pierda si se intenta borrar el cliente, el usuario,
    una moneda o un medio de pago.

    Attributes:
        id: Identificador UUID, no editable.
        cliente: Cliente en nombre del cual se realizó la operación.
        usuario: Usuario asociado al cliente que realizó la operación.
        cajero: Usuario (rol `Cajero`) que confirmó la operación. Vacío
            mientras la transacción esté `PENDIENTE`.
        tipo: `COMPRA` o `VENTA`.
        moneda: Divisa operada.
        medio_pago: Medio de pago utilizado.
        monto_pagado: Monto entregado por el cliente.
        monto_recibido: Monto recibido por el cliente.
        tasa_aplicada: Precio en PYG de una unidad de la divisa.
        facturada: Si se emitió factura de la operación.
        dispositivo: Tipo de dispositivo desde el que se realizó
            (ver `operaciones.utils.detectar_dispositivo`).
        estado: `PENDIENTE`, `CONFIRMADA` o `CANCELADA`.
        fecha: Fecha y hora de la operación.
    """

    class Tipo(models.TextChoices):
        """Tipo de operación desde el punto de vista del cliente."""
        COMPRA = 'COMPRA', 'Compra'
        VENTA = 'VENTA', 'Venta'

    class Dispositivo(models.TextChoices):
        """Dispositivos reconocidos a partir del User-Agent del navegador."""
        IPHONE = 'IPHONE', 'iPhone'
        IPAD = 'IPAD', 'iPad'
        ANDROID = 'ANDROID', 'Android'
        WINDOWS = 'WINDOWS', 'PC (Windows)'
        MAC = 'MAC', 'Mac'
        LINUX = 'LINUX', 'PC (Linux)'
        OTRO = 'OTRO', 'Otro'

    class Estado(models.TextChoices):
        """Estados de la transacción (la lógica de cambio de estado es de otra historia)."""
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        CONFIRMADA = 'CONFIRMADA', 'Confirmada'
        CANCELADA = 'CANCELADA', 'Cancelada'

    MONEDA_LOCAL = 'PYG'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='transacciones')
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='transacciones_realizadas'
    )
    cajero = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='transacciones_atendidas'
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, related_name='transacciones')
    medio_pago = models.ForeignKey('mpagos.MedioPago', on_delete=models.PROTECT, related_name='transacciones')
    monto_pagado = models.DecimalField(max_digits=18, decimal_places=2)
    monto_recibido = models.DecimalField(max_digits=18, decimal_places=2)
    tasa_referencia = models.ForeignKey(TasaDeCambio, on_delete=models.PROTECT, related_name='transacciones')
    tasa_aplicada = models.DecimalField(max_digits=18, decimal_places=4)
    categoria_cliente_aplicada = models.CharField(max_length=20, choices=Cliente.Categoria.choices)
    porcentaje_comision = models.DecimalField(max_digits=5, decimal_places=2)
    monto_comision = models.DecimalField(max_digits=18, decimal_places=4)
    moneda_comision = models.CharField(max_length=3)    
    facturada = models.BooleanField(default=False)
    dispositivo = models.CharField(max_length=10, choices=Dispositivo.choices, default=Dispositivo.OTRO)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    # default en lugar de auto_now_add para poder registrar operaciones con fecha pasada
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        """Nombres legibles, orden de más reciente a más antigua e índice por cliente."""
        verbose_name = "Transacción"
        verbose_name_plural = "Transacciones"
        ordering = ['-fecha']
        indexes = [models.Index(fields=['cliente', '-fecha'])]

    def __str__(self):
        """Devuelve `TIPO MONEDA - cliente (dd/mm/aaaa hh:mm)`."""
        return f"{self.get_tipo_display()} {self.moneda.codigo} - {self.cliente} ({self.fecha:%d/%m/%Y %H:%M})"

    @property
    def moneda_pagada(self):
        """Código de la moneda que entregó el cliente.

        Returns:
            str: `PYG` en una compra; el código de la divisa en una venta.
        """
        return self.MONEDA_LOCAL if self.tipo == self.Tipo.COMPRA else self.moneda.codigo

    @property
    def moneda_recibida(self):
        """Código de la moneda que recibió el cliente.

        Returns:
            str: El código de la divisa en una compra; `PYG` en una venta.
        """
        return self.moneda.codigo if self.tipo == self.Tipo.COMPRA else self.MONEDA_LOCAL

    """Modelos de la aplicación operaciones (monedas, tasas de cambio y transacciones)."""

from django.db import models
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from clientes.models import Cliente


class Moneda(models.Model):
    """Moneda extranjera operada por la casa de cambios.

    Attributes:
        id: Identificador UUID, no editable.
        codigo: Código ISO 4217 de 3 letras (ej. `USD`), único.
        nombre: Nombre de la moneda.
        habilitada: Si la moneda se muestra y puede operarse.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=3, unique=True)  # ISO 4217
    nombre = models.CharField(max_length=50)
    habilitada = models.BooleanField(default=True)

    def __str__(self):
        """Devuelve el código ISO de la moneda."""
        return self.codigo

    class Meta:
        """Nombres legibles y orden alfabético por código."""
        verbose_name = "Moneda"
        verbose_name_plural = "Monedas"
        ordering = ['codigo']


class TasaDeCambio(models.Model):
    """Tasa de cambio de una moneda respecto al guaraní (PYG).

    Cada registro es histórico: la tasa vigente es la más reciente
    (ordenadas por `fecha_vigencia` descendente).

    Attributes:
        moneda: Moneda a la que pertenece la tasa.
        tasa_base: Valor de referencia en PYG.
        margen_compra: Monto que se resta a la base para el precio de compra.
        margen_venta: Monto que se suma a la base para el precio de venta.
        fecha_vigencia: Fecha y hora de registro de la tasa.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    moneda = models.ForeignKey(Moneda, on_delete=models.CASCADE, related_name='tasas')
    tasa_base = models.DecimalField(max_digits=12, decimal_places=4)
    margen_compra = models.DecimalField(max_digits=12, decimal_places=4)
    margen_venta = models.DecimalField(max_digits=12, decimal_places=4)
    fecha_vigencia = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Nombres legibles y orden de más reciente a más antigua."""
        verbose_name = "Tasa de Cambio"
        verbose_name_plural = "Tasas de Cambio"
        ordering = ['-fecha_vigencia']

    def __str__(self):
        """Devuelve `MONEDA @ dd/mm/aaaa hh:mm`."""
        return f"{self.moneda.codigo} @ {self.fecha_vigencia:%d/%m/%Y %H:%M}"

    def calcular_precio_compra(self):
        """Calcula el precio al que la casa compra la moneda.

        Returns:
            Decimal: `tasa_base - margen_compra`.
        """
        return self.tasa_base - self.margen_compra

    def calcular_precio_venta(self):
        """Calcula el precio al que la casa vende la moneda.

        Returns:
            Decimal: `tasa_base + margen_venta`.
        """
        return self.tasa_base + self.margen_venta

class ConfiguracionComision(models.Model):
    """Comision vigente segun la categoria del cliente"""

    id=models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    categoria = models.CharField(max_length=20, choices=Cliente.Categoria.choices, unique=True)
    porcentaje = models.DecimalField(max_digits=5,decimal_places=2,validators=[MinValueValidator(0),MaxValueValidator(100)])
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_categoria_display()} - {self.porcentaje}%"


class Transaccion(models.Model):
    """Operación de compra o venta de divisas realizada en nombre de un cliente.

    Un cliente puede tener varios usuarios asociados que operan en su nombre
    y un usuario puede operar para varios clientes: `cliente` indica a nombre
    de quién se hizo la operación y `usuario`, quién la realizó.

    El tipo se interpreta desde el punto de vista del cliente:

    - `COMPRA`: el cliente paga guaraníes (PYG) y recibe la divisa.
    - `VENTA`: el cliente paga la divisa y recibe guaraníes (PYG).

    Los registros son de auditoría: las claves foráneas usan `PROTECT` para
    que el historial no se pierda si se intenta borrar el cliente, el usuario,
    una moneda o un medio de pago.

    Attributes:
        id: Identificador UUID, no editable.
        cliente: Cliente en nombre del cual se realizó la operación.
        usuario: Usuario asociado al cliente que realizó la operación.
        cajero: Usuario (rol `Cajero`) que confirmó la operación. Vacío
            mientras la transacción esté `PENDIENTE`.
        tipo: `COMPRA` o `VENTA`.
        moneda: Divisa operada.
        medio_pago: Medio de pago utilizado.
        monto_pagado: Monto entregado por el cliente.
        monto_recibido: Monto recibido por el cliente.
        tasa_aplicada: Precio en PYG de una unidad de la divisa.
        facturada: Si se emitió factura de la operación.
        dispositivo: Tipo de dispositivo desde el que se realizó
            (ver `operaciones.utils.detectar_dispositivo`).
        estado: `PENDIENTE`, `CONFIRMADA` o `CANCELADA`.
        fecha: Fecha y hora de la operación.
    """

    class Tipo(models.TextChoices):
        """Tipo de operación desde el punto de vista del cliente."""
        COMPRA = 'COMPRA', 'Compra'
        VENTA = 'VENTA', 'Venta'

    class Dispositivo(models.TextChoices):
        """Dispositivos reconocidos a partir del User-Agent del navegador."""
        IPHONE = 'IPHONE', 'iPhone'
        IPAD = 'IPAD', 'iPad'
        ANDROID = 'ANDROID', 'Android'
        WINDOWS = 'WINDOWS', 'PC (Windows)'
        MAC = 'MAC', 'Mac'
        LINUX = 'LINUX', 'PC (Linux)'
        OTRO = 'OTRO', 'Otro'

    class Estado(models.TextChoices):
        """Estados de la transacción (la lógica de cambio de estado es de otra historia)."""
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        CONFIRMADA = 'CONFIRMADA', 'Confirmada'
        CANCELADA = 'CANCELADA', 'Cancelada'

    MONEDA_LOCAL = 'PYG'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='transacciones')
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='transacciones_realizadas'
    )
    cajero = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='transacciones_atendidas'
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, related_name='transacciones')
    medio_pago = models.ForeignKey('mpagos.MedioPago', on_delete=models.PROTECT, related_name='transacciones')
    monto_pagado = models.DecimalField(max_digits=18, decimal_places=2)
    monto_recibido = models.DecimalField(max_digits=18, decimal_places=2)
    tasa_referencia = models.ForeignKey(TasaDeCambio, on_delete=models.PROTECT, related_name='transacciones')
    tasa_aplicada = models.DecimalField(max_digits=18, decimal_places=4)
    categoria_cliente_aplicada = models.CharField(max_length=20, choices=Cliente.Categoria.choices)
    porcentaje_comision = models.DecimalField(max_digits=5, decimal_places=2)
    monto_comision = models.DecimalField(max_digits=18, decimal_places=4)
    moneda_comision = models.CharField(max_length=3)    
    facturada = models.BooleanField(default=False)
    dispositivo = models.CharField(max_length=10, choices=Dispositivo.choices, default=Dispositivo.OTRO)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    # default en lugar de auto_now_add para poder registrar operaciones con fecha pasada
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        """Nombres legibles, orden de más reciente a más antigua e índice por cliente."""
        verbose_name = "Transacción"
        verbose_name_plural = "Transacciones"
        ordering = ['-fecha']
        indexes = [models.Index(fields=['cliente', '-fecha'])]

    def __str__(self):
        """Devuelve `TIPO MONEDA - cliente (dd/mm/aaaa hh:mm)`."""
        return f"{self.get_tipo_display()} {self.moneda.codigo} - {self.cliente} ({self.fecha:%d/%m/%Y %H:%M})"

    @property
    def moneda_pagada(self):
        """Código de la moneda que entregó el cliente.

        Returns:
            str: `PYG` en una compra; el código de la divisa en una venta.
        """
        return self.MONEDA_LOCAL if self.tipo == self.Tipo.COMPRA else self.moneda.codigo

    @property
    def moneda_recibida(self):
        """Código de la moneda que recibió el cliente.

        Returns:
            str: El código de la divisa en una compra; `PYG` en una venta.
        """
        return self.moneda.codigo if self.tipo == self.Tipo.COMPRA else self.MONEDA_LOCAL

def es_tasa_vigente(self):
    """Verifica si la tasa asociada sigue siendo la más reciente para su moneda."""
    ultima_tasa = TasaDeCambio.objects.filter(
        moneda=self.moneda
    ).order_by('-fecha_vigencia').first()

    return ultima_tasa is not None and ultima_tasa.id == self.tasa_referencia_id