"""
Formularios web para la gestión de Clientes y asignación de cuentas.

Contiene la lógica de captura e ingreso de datos para:
- Registro simplificado de Persona Física.
- Registro/Edición completa de Clientes.
- Asignación administrativa de Usuarios a Clientes.
"""

from django import forms
from .models import Cliente, UsuarioCliente


class ClienteFisicaForm(forms.ModelForm):
    """
    Formulario simplificado usado por un usuario común para registrar su
    propio perfil de Persona Física.
    """

    class Meta:
        model = Cliente
        # Se omiten campos administrativos como tipo_persona o categoría
        fields = ['nombre_o_denominacion', 'documento']


class ClienteForm(forms.ModelForm):
    """Formulario completo para crear y editar cualquier tipo de Cliente desde el panel admin."""

    class Meta:
        model = Cliente
        # Incluye todos los campos editables por administradores
        fields = ['tipo_persona', 'nombre_o_denominacion', 'documento', 'categoria']


class AsignacionForm(forms.ModelForm):
    """Formulario para asociar un Usuario con un Cliente desde el panel administrativo."""

    class Meta:
        model = UsuarioCliente
        fields = ['usuario', 'cliente']

    def clean(self):
        """
        Ejecuta las validaciones de negocio en el formulario para capturar
        errores de validación antes de procesar el guardado.

        Returns:
            dict: Datos limpios y convalidados del formulario.
        """
        cleaned_data = super().clean()
        usuario = cleaned_data.get('usuario')
        cliente = cleaned_data.get('cliente')

        # Se simula la instancia para validar las reglas antes de tocar la BD
        if usuario and cliente:
            instancia_temp = UsuarioCliente(usuario=usuario, cliente=cliente)
            instancia_temp.clean() # Dispara la validación de Persona Física
        return cleaned_data