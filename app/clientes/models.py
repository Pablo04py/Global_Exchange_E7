"""Modelos de la aplicación clientes."""

from django.db import models
import uuid
from django.db import models
from usuarios.models import Usuario

class Cliente (models.Model):
    """Cliente de la casa de cambios (persona física o jurídica).

    Attributes:
        id: Identificador UUID, no editable.
        tipo_persona: `FISICA` o `JURIDICA`.
        nombre_o_denominacion: Nombre completo o razón social.
        documento: Cédula o RUC, único en el sistema.
        categoria: `MINORISTA`, `CORPORATIVO` o `VIP`.
        fecha_registro: Fecha de alta del cliente.
    """
    class TipoPersona(models.TextChoices):
        """Tipos de persona admitidos para un cliente."""
        FISICA = 'FISICA', 'Física'
        JURIDICA = 'JURIDICA', 'Jurídica'

    class Categoria(models.TextChoices):
        """Categorías de cliente (pueden condicionar las tasas aplicadas)."""
        MINORISTA = 'MINORISTA', 'Minorista'
        CORPORATIVO = 'CORPORATIVO', 'Corporativo'
        VIP = 'VIP', 'VIP'

    id  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  #identificador unico y no editable
    tipo_persona = models.CharField(max_length = 10, choices= TipoPersona.choices)
    nombre_o_denominacion = models.CharField(max_length=255)
    documento = models.CharField(max_length=50, unique=True)
    categoria = models.CharField(max_length=20, choices=Categoria.choices, default=Categoria.MINORISTA)
    fecha_registro = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        """Devuelve el nombre o denominación del cliente."""
        return self.nombre_o_denominacion #pa leeer

    def recalcular_categoria(self):
        """Recalcula la categoría del cliente.

        Pendiente de implementación.
        """
        # dsps
        pass

class UsuarioCliente(models.Model):
    """Asociación entre un usuario del sistema y un cliente.

    Un usuario puede operar en nombre de varios clientes y un cliente puede
    tener varios usuarios asociados. La pareja (usuario, cliente) es única.
    """
    class RolCliente(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        OPERADOR = 'OPERADOR', 'Operador'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='clientes_asociados')
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='usuarios_asociados')
    rol_cliente = models.CharField(max_length=20, choices=RolCliente.choices, default=RolCliente.OPERADOR)
    fecha_asociacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Garantiza que la asociación usuario-cliente no se repita."""
        unique_together = ('usuario', 'cliente')  # evita duplicar la misma asociacion debe ser unica en la bd

    def __str__(self):
        return (
            f"{self.usuario.username} → "
            f"{self.cliente.nombre_o_denominacion} "
            f"({self.get_rol_cliente_display()})"
        )