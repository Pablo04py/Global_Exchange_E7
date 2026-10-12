import uuid
from django.db import models
from django.conf import settings
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils import timezone


MENSAJE_INMUTABLE = (
    "Los registros de caja no se pueden editar ni borrar. "
    "Un error se corrige con un movimiento de AJUSTE inverso."
)


class EstadoCaja(models.TextChoices):
    DISPONIBLE = 'DISPONIBLE', 'Disponible'
    EN_USO = 'EN_USO', 'En Uso'
    INACTIVA = 'INACTIVA', 'Inactiva'
    MANTENIMIENTO = 'MANTENIMIENTO', 'En Mantenimiento'


class EstadoSesionCaja(models.TextChoices):
    ASIGNADA = 'ASIGNADA', 'Asignada'
    ABIERTA = 'ABIERTA', 'Abierta'
    EN_ARQUEO = 'EN_ARQUEO', 'En Arqueo'
    CERRADA = 'CERRADA', 'Cerrada'


class RegistroInmutableQuerySet(models.QuerySet):
    """Bloquea las modificaciones masivas: update(), bulk_update() y delete()."""

    def update(self, *args, **kwargs):
        raise ValidationError(MENSAJE_INMUTABLE)

    def bulk_update(self, *args, **kwargs):
        raise ValidationError(MENSAJE_INMUTABLE)

    def delete(self):
        raise ValidationError(MENSAJE_INMUTABLE)


class RegistroInmutable(models.Model):
    """Base para registros que solo se pueden insertar (libro mayor)."""
    objects = RegistroInmutableQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError(MENSAJE_INMUTABLE)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(MENSAJE_INMUTABLE)


class Caja(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, unique=True)
    codigo = models.CharField(max_length=20, unique=True)
    estado = models.CharField(
        max_length=20,
        choices=EstadoCaja.choices,
        default=EstadoCaja.DISPONIBLE
    )
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'caja'
        verbose_name = 'Caja'
        verbose_name_plural = 'Cajas'

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class SesionCaja(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    caja = models.ForeignKey(Caja, on_delete=models.PROTECT, related_name='sesiones')

    cajero = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='sesiones_cajero'
    )
    asignado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='sesiones_asignadas_por'
    )

    estado = models.CharField(
        max_length=20,
        choices=EstadoSesionCaja.choices,
        default=EstadoSesionCaja.ASIGNADA
    )

    # Solo guaraníes y solo informativos. El stock real sale de MovimientoCaja.
    monto_inicial = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    monto_final_declarado = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    monto_final_sistema = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_apertura = models.DateTimeField(null=True, blank=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'sesion_caja'
        verbose_name = 'Sesión de Caja'
        verbose_name_plural = 'Sesiones de Caja'
        ordering = ['-fecha_asignacion']

    def __str__(self):
        return f"Sesión {self.caja.codigo} - Cajero: {self.cajero} [{self.estado}]"


class SentidoMovimiento(models.TextChoices):
    ENTRADA = 'ENTRADA', 'Entrada'
    SALIDA = 'SALIDA', 'Salida'


class TipoMovimiento(models.TextChoices):
    APERTURA = 'APERTURA', 'Apertura'
    OPERACION = 'OPERACION', 'Operación de cambio'
    TRANSFERENCIA = 'TRANSFERENCIA', 'Transferencia entre cajas'
    AJUSTE = 'AJUSTE', 'Ajuste'


class MovimientoCaja(RegistroInmutable):
    """Libro mayor de la caja: cada fila es una entrada o salida de efectivo."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sesion = models.ForeignKey(SesionCaja, on_delete=models.PROTECT, related_name='movimientos')
    transaccion = models.ForeignKey(
        'operaciones.Transaccion', on_delete=models.PROTECT,
        null=True, blank=True, related_name='movimientos_caja',
    )
    tipo = models.CharField(max_length=20, choices=TipoMovimiento.choices)
    sentido = models.CharField(max_length=10, choices=SentidoMovimiento.choices)
    moneda = models.CharField(max_length=3)
    monto = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(0.01)])
    justificacion = models.CharField(max_length=255, blank=True)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'movimiento_caja'
        ordering = ['-fecha']
        indexes = [models.Index(fields=['sesion', 'moneda'])]
        constraints = [
            models.UniqueConstraint(
                fields=['transaccion', 'sentido'],
                condition=Q(transaccion__isnull=False),
                name='uniq_movimiento_por_transaccion_y_sentido',
            ),
        ]

    def save(self, *args, **kwargs):
        # Los validators del campo no corren en .create(); lo exigimos acá.
        if self.monto is None or self.monto <= 0:
            raise ValidationError("El monto del movimiento debe ser mayor a cero.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sentido} {self.monto} {self.moneda} ({self.tipo})"


class ArqueoCaja(RegistroInmutable):
    """Resultado del cierre: una fila por moneda comparando lo declarado contra el sistema."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sesion = models.ForeignKey(SesionCaja, on_delete=models.PROTECT, related_name='arqueos')
    moneda = models.CharField(max_length=3)
    monto_sistema = models.DecimalField(max_digits=18, decimal_places=2)
    monto_declarado = models.DecimalField(max_digits=18, decimal_places=2)
    # declarado - sistema: positivo = sobrante, negativo = faltante
    diferencia = models.DecimalField(max_digits=18, decimal_places=2)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'arqueo_caja'
        ordering = ['sesion', 'moneda']
        constraints = [
            models.UniqueConstraint(fields=['sesion', 'moneda'], name='uniq_arqueo_por_sesion_y_moneda'),
        ]

    @property
    def resultado(self):
        if self.diferencia > 0:
            return 'sobrante'
        if self.diferencia < 0:
            return 'faltante'
        return 'cuadrado'

    def __str__(self):
        return f"Arqueo {self.moneda}: {self.resultado} ({self.diferencia})"