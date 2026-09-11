"""
Módulo de modelos de datos para la gestión de Medios de Pago (mpagos).

Define la estructura de la entidad MedioPago para registrar y administrar
los métodos de acreditación/cobro de los clientes de la casa de cambio.
"""

from django.db import models
from django.conf import settings


class MedioPago(models.Model):
    """
    Representa un medio de pago registrado por un usuario/cliente en el sistema.

    Soporta tarjetas de crédito/débito, transferencias bancarias SIPAP y efectivo.
    Aplica enmascaramiento sobre los datos sensibles antes de la persistencia.
    """

    # Opciones de tipos de medios de pago nacionales habilitados
    TIPO_CHOICES = [
        ('TARJETA', 'Tarjeta de Crédito / Débito'),
        ('SIPAP', 'Transferencia Bancaria (SIPAP)'),
        ('EFECTIVO', 'Efectivo en Caja'),
    ]

    # Relación de pertenencia con el modelo de Usuario/Cliente de Django
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='medios_pago',
        help_text="Usuario propietario de este medio de pago."
    )

    # Identificación básica del medio de pago
    tipo = models.CharField(
        max_length=20, 
        choices=TIPO_CHOICES,
        help_text="Tipo de método de pago nacional habilitado."
    )
    
    nombre_titular = models.CharField(
        max_length=150, 
        verbose_name="Nombre del Titular",
        help_text="Nombre completo del titular de la cuenta o tarjeta."
    )
    
    banco_emisor = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name="Banco Emisor",
        help_text="Entidad bancaria o financiera emisora (ej. Itaú, Continental)."
    )

    # Registro enmascarado por seguridad de datos sensibles
    numero_enmascarado = models.CharField(
        max_length=30, 
        help_text="Número o identificador enmascarado. Ej: **** 4321 o Alias CBU/Cuenta."
    )

    # Banderas de estado operativo
    es_predeterminado = models.BooleanField(
        default=False, 
        verbose_name="¿Es Predeterminado?",
        help_text="Indica si es el medio de pago seleccionado por defecto."
    )
    
    activo = models.BooleanField(
        default=True,
        help_text="Indica si el registro está activo (borrado lógico)."
    )
    
    creado_en = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de registro en el sistema."
    )

    class Meta:
        """Configuración de metadatos del modelo en la base de datos."""
        verbose_name = "Medio de Pago"
        verbose_name_plural = "Medios de Pago"
        ordering = ['-es_predeterminado', '-creado_en']

    def __str__(self):
        """
        Retorna la representación textual del medio de pago.

        Returns:
            str: Tipo, identificador enmascarado y titular.
        """
        # Formato accesible para desplegar en listas y selectores de la interfaz
        return f"{self.get_tipo_display()} - {self.numero_enmascarado} ({self.nombre_titular})"