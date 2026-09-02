"""
Modelos de datos para el módulo de Clientes.

Define las entidades principales:
- `Cliente`: Representa a personas físicas o empresas en el sistema.
- `UsuarioCliente`: Tabla intermedia (N:N) que relaciona usuarios con clientes.
"""

from django.db import models
from django.core.exceptions import ValidationError
import uuid
from usuarios.models import Usuario


class Cliente(models.Model):
    """
    Representa a un cliente dentro de la base de datos de la casa de cambio.

    Attributes:
        id (UUID): Identificador único universal para evitar secuencias predecibles.
        tipo_persona (str): Indica si el cliente es Persona Física o Jurídica.
        nombre_o_denominacion (str): Nombre completo de la persona o razón social.
        documento (str): Documento de identidad o RUC (debe ser único).
        categoria (str): Clasificación comercial (Minorista, Corporativo, VIP).
        fecha_registro (datetime): Marca de tiempo de cuándo fue registrado.
    """

    class TipoPersona(models.TextChoices):
        """Opciones disponibles para el tipo de persona."""
        FISICA = 'FISICA', 'Física'
        JURIDICA = 'JURIDICA', 'Jurídica'

    class Categoria(models.TextChoices):
        """Categorías comerciales asignables al cliente."""
        MINORISTA = 'MINORISTA', 'Minorista'
        CORPORATIVO = 'CORPORATIVO', 'Corporativo'
        VIP = 'VIP', 'VIP'

    # ID único generado automáticamente con UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo_persona = models.CharField(max_length=10, choices=TipoPersona.choices)
    nombre_o_denominacion = models.CharField(max_length=255)
    
    # Documento único para evitar duplicados en la base de datos
    documento = models.CharField(max_length=50, unique=True)
    categoria = models.CharField(max_length=20, choices=Categoria.choices, default=Categoria.MINORISTA)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Devuelve el nombre del cliente para mostrarlo en el admin o plantillas."""
        # Muestra el nombre directamente en listados y selectores
        return self.nombre_o_denominacion

    def recalcular_categoria(self):
        """
        Método reservado para actualizar la categoría del cliente automáticamente
        basado en el volumen de sus transacciones.
        """
        # Reservado para lógica comercial futura
        pass


class UsuarioCliente(models.Model):
    """
    Tabla intermedia que conecta un Usuario con uno o varios Clientes.

    Reglas de negocio aplicadas:
    - Un usuario y un cliente no pueden duplicar su relación exacta.
    - Si el cliente es Persona Física, solo puede tener UN único usuario asociado.

    Attributes:
        id (UUID): Identificador único de la relación.
        usuario (ForeignKey): Enlace al modelo de Usuario.
        cliente (ForeignKey): Enlace al modelo de Cliente.
        fecha_asociacion (datetime): Fecha en que se realizó el vínculo.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='clientes_asociados')
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='usuarios_asociados')
    fecha_asociacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Configuración de metadatos del modelo."""
        # Evita repetir exactamente el mismo vínculo en la base de datos
        unique_together = ('usuario', 'cliente')

    def clean(self):
        """
        Valida que se cumplan las reglas de negocio antes de guardar en la BD.

        Raises:
            ValidationError: Si se intenta asignar más de un usuario a un
            cliente registrado como Persona Física.
        """
        super().clean()

        # Si faltan datos en la relación, aborta la validación temprana
        if not self.cliente_id or not self.usuario_id:
            return

        # REGLA DE NEGOCIO: Si es Persona Física, no se permite asociar más de 1 usuario
        if self.cliente.tipo_persona == Cliente.TipoPersona.FISICA:
            # Filtramos si ya existe otra asociación previa para este mismo cliente
            usuarios_asociados = UsuarioCliente.objects.filter(cliente=self.cliente).exclude(pk=self.pk)
            if usuarios_asociados.exists():
                # Lanza el error impidiendo la operación
                raise ValidationError(
                    f"El cliente '{self.cliente.nombre_o_denominacion}' es Persona Física y ya tiene un usuario asignado."
                )

    def save(self, *args, **kwargs):
        """
        Sobrescribe el guardado por defecto para asegurar la ejecución
        de las validaciones de `clean()`.
        """
        # Garantiza que clean() se ejecute siempre antes de escribir en PostgreSQL
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """Devuelve la representación en texto de la relación Usuario -> Cliente."""
        # Representación legible para debugging y vistas
        return f"{self.usuario.username} → {self.cliente.nombre_o_denominacion}"