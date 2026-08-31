from django.db import models
import uuid
from django.db import models
from usuarios.models import Usuario

class Cliente (models.Model):
    class TipoPersona(models.TextChoices):
        FISICA = 'FISICA', 'Física'
        JURIDICA = 'JURIDICA', 'Jurídica'

    class Categoria(models.TextChoices):
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
        return self.nombre_o_denominacion #pa leeer

    def recalcular_categoria(self):
        # dsps
        pass

class UsuarioCliente(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='clientes_asociados')
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='usuarios_asociados')
    fecha_asociacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'cliente')  # evita duplicar la misma asociacion debe ser unica en la bd

    def __str__(self):
        return f"{self.usuario.username} → {self.cliente.nombre_o_denominacion}"