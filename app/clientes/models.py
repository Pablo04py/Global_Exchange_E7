from django.db import models
from django.core.exceptions import ValidationError
import uuid
from usuarios.models import Usuario

class Cliente(models.Model):
    class TipoPersona(models.TextChoices):
        FISICA = 'FISICA', 'Física'
        JURIDICA = 'JURIDICA', 'Jurídica'

    class Categoria(models.TextChoices):
        MINORISTA = 'MINORISTA', 'Minorista'
        CORPORATIVO = 'CORPORATIVO', 'Corporativo'
        VIP = 'VIP', 'VIP'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo_persona = models.CharField(max_length=10, choices=TipoPersona.choices)
    nombre_o_denominacion = models.CharField(max_length=255)
    documento = models.CharField(max_length=50, unique=True)
    categoria = models.CharField(max_length=20, choices=Categoria.choices, default=Categoria.MINORISTA)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre_o_denominacion

    def recalcular_categoria(self):
        pass


class UsuarioCliente(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='clientes_asociados')
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='usuarios_asociados')
    fecha_asociacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'cliente')  # Evita duplicar la misma relación exacta

    def clean(self):
        super().clean()

        if not self.cliente_id or not self.usuario_id:
            return

        # Única Regla de Control:
        # Si el Cliente es Persona FISICA, se verifica que no tenga ya OTRO usuario asignado.
        if self.cliente.tipo_persona == Cliente.TipoPersona.FISICA:
            usuarios_asociados = UsuarioCliente.objects.filter(cliente=self.cliente).exclude(pk=self.pk)
            if usuarios_asociados.exists():
                raise ValidationError(
                    f"El cliente '{self.cliente.nombre_o_denominacion}' es Persona Física y ya tiene un usuario asignado."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usuario.username} → {self.cliente.nombre_o_denominacion}"