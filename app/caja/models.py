import uuid
from django.db import models
from django.conf import settings


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


class SaldoInicialCaja(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sesion = models.ForeignKey(
        SesionCaja, 
        on_delete=models.CASCADE, 
        related_name='saldos_iniciales'
    )
    # Relación dinámica con el modelo Moneda de la app operaciones
    moneda = models.ForeignKey(
        'operaciones.Moneda', 
        on_delete=models.PROTECT, 
        related_name='saldos_iniciales'
    )
    monto = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

    class Meta:
        db_table = 'saldo_inicial_caja'
        unique_together = ('sesion', 'moneda')
        verbose_name = 'Saldo Inicial de Caja'
        verbose_name_plural = 'Saldos Iniciales de Caja'

    def __str__(self):
        return f"{self.moneda.codigo}: {self.monto} (Sesión {self.sesion.caja.codigo})"