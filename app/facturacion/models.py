import uuid
from datetime import date

from django.core.validators import MinValueValidator
from django.db import models


def actividades_economicas_default():
        return [
            {
                'cActEco': '62010',
                'dDesActEco': 'Actividades de programación informática'
            },
            {
                'cActEco': '74909',
                'dDesActEco': 'Otras actividades profesionales, científicas y técnicas n.c.p.'
            }
        ]


class ConfiguracionFacturacion(models.Model):
    """
    Configuración fiscal del emisor de las facturas electrónicas.

    En Global Exchange existe un único emisor:
    Global Exchange.
    """

    class TipoContribuyente(models.IntegerChoices):
        PERSONA_FISICA = 1, 'Persona Física'
        PERSONA_JURIDICA = 2, 'Persona Jurídica'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    nombre_emisor = models.CharField(
        max_length=255,
        verbose_name='Razón social del emisor'
    )

    ruc_emisor = models.CharField(
        max_length=20,
        default='2595733',
        verbose_name='RUC del emisor'
    )

    dv_emisor = models.CharField(
        max_length=1,
        default='3',
        verbose_name='Dígito verificador del emisor'
    )

    tipo_contribuyente = models.PositiveSmallIntegerField(
        choices=TipoContribuyente.choices,
        default=TipoContribuyente.PERSONA_FISICA
    )

    timbrado = models.CharField(
        max_length=20,
        default='02595733',
        verbose_name='Número de timbrado'
    )

    fecha_inicio_timbrado = models.DateField(
        default=date(2025, 3, 27),
        verbose_name='Fecha de inicio del timbrado'
    )

    establecimiento = models.CharField(
        max_length=3,
        default='001'
    )

    punto_expedicion = models.CharField(
        max_length=3,
        default='003',
        verbose_name='Punto de expedición'
    )

    direccion = models.CharField(
        max_length=255,
        verbose_name='Dirección del emisor'
    )

    numero_casa = models.CharField(
        max_length=10,
        default='0',
        verbose_name='Número de casa'
    )

    departamento_codigo = models.CharField(
        max_length=5,
        null=True,
        blank=True,
        verbose_name='Código de departamento'
    )

    departamento_descripcion = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Departamento'
    )

    ciudad_codigo = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name='Código de ciudad'
    )

    ciudad_descripcion = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Ciudad'
    )

    telefono = models.CharField(
        max_length=30,
        default='(021)5887000',
        blank=True
    )

    email = models.EmailField(
        blank=True
    )

    actividades_economicas = models.JSONField(
        default=actividades_economicas_default,
        blank=True,
        verbose_name='Actividades económicas'
    )

    siguiente_numero_documento = models.PositiveIntegerField(
        default=216,
        validators=[MinValueValidator(1)],
        verbose_name='Siguiente número de factura'
    )

    activa = models.BooleanField(
        default=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = 'Configuración de facturación'
        verbose_name_plural = 'Configuraciones de facturación'

    def __str__(self):
        return (
            f"{self.nombre_emisor} - "
            f"RUC {self.ruc_emisor}-{self.dv_emisor}"
        )

class FacturaElectronica(models.Model):
    """
    Factura electrónica asociada a una transacción de Global Exchange.

    Cada transacción puede generar como máximo una factura electrónica.
    """

    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        CALCULADA = 'CALCULADA', 'Calculada'
        EMITIDA = 'EMITIDA', 'Emitida'
        APROBADA = 'APROBADA', 'Aprobada'
        RECHAZADA = 'RECHAZADA', 'Rechazada'
        ERROR = 'ERROR', 'Error'
        ANULADA = 'ANULADA', 'Anulada'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    transaccion = models.OneToOneField(
        'operaciones.Transaccion',
        on_delete=models.PROTECT,
        related_name='factura'
    )

    configuracion = models.ForeignKey(
        ConfiguracionFacturacion,
        on_delete=models.PROTECT,
        related_name='facturas'
    )

    numero_documento = models.CharField(
        max_length=7,
        verbose_name='Número de factura'
    )

    cdc = models.CharField(
        max_length=44,
        unique=True,
        null=True,
        blank=True,
        verbose_name='CDC'
    )

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )

    operation_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='ID de operación de Factura Segura'
    )

    codigo_respuesta = models.IntegerField(
        null=True,
        blank=True
    )

    descripcion_respuesta = models.TextField(
        blank=True
    )

    json_resumido = models.JSONField(
        null=True,
        blank=True
    )

    json_calculado = models.JSONField(
        null=True,
        blank=True
    )

    json_respuesta_generacion = models.JSONField(
        null=True,
        blank=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

    fecha_aprobacion = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Factura electrónica'
        verbose_name_plural = 'Facturas electrónicas'

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'configuracion',
                    'numero_documento'
                ],
                name='factura_numero_unico_por_configuracion'
            )
        ]

        ordering = ['-fecha_creacion']

    def __str__(self):
        return (
            f"Factura {self.numero_documento} "
            f"- {self.get_estado_display()}"
        )