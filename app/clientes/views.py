"""Vistas de la aplicación clientes (CRUD, asignación y registro como cliente)."""

from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Cliente, UsuarioCliente
from .forms import ClienteForm, AsignacionForm
from .forms import ClienteFisicaForm
from usuarios.decorators import requiere_rol
# read
@requiere_rol('Administrador General')
def lista_clientes(request):
    """Lista todos los clientes registrados.

    Solo para el rol `Administrador General`.

    Args:
        request: Petición HTTP.

    Returns:
        HttpResponse: Plantilla `clientes/lista_clientes.html`.
    """
    # Filtrar  clientes para que solo traiga los que están asociados al usuario logueado
    clientes = Cliente.objects.all() 
    
    return render(request, 'clientes/lista_clientes.html', {'clientes': clientes})  

# Para cualquier usuario logueado: sus propios clientes operables
@login_required
def mis_clientes(request):
    """Lista los clientes asociados al usuario autenticado.

    Args:
        request: Petición HTTP.

    Returns:
        HttpResponse: Plantilla `clientes/mis_clientes.html`.
    """
    clientes = Cliente.objects.filter(usuarios_asociados__usuario=request.user)
    return render(request, 'clientes/mis_clientes.html', {'clientes': clientes})

# create

@requiere_rol('Administrador General')
def crear_cliente(request):
    """Muestra y procesa el formulario de alta de un cliente.

    Solo para el rol `Administrador General`. Si el formulario es válido,
    redirige al listado de clientes.

    Args:
        request: Petición HTTP (GET muestra el formulario, POST lo guarda).

    Returns:
        HttpResponse: Formulario o redirección a `lista_clientes`.
    """
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save() 
            return redirect('lista_clientes')
    else:
        form = ClienteForm()
    return render(request, 'clientes/form_cliente.html', {'form': form})

#update
@requiere_rol('Administrador General')
def editar_cliente(request, cliente_id):
    """Muestra y procesa el formulario de edición de un cliente.

    Solo para el rol `Administrador General`.

    Args:
        request: Petición HTTP.
        cliente_id: UUID del cliente a editar.

    Returns:
        HttpResponse: Formulario o redirección a `lista_clientes`.

    Raises:
        Http404: Si el cliente no existe.
    """
    # El get_object_or_404 con filter asegura que si el usuario intenta 
    # editar el cliente de otro poniendo el ID en la URL, le de error 404.
    cliente = get_object_or_404(Cliente, id=cliente_id)
    
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect('lista_clientes')
    else:
        form = ClienteForm(instance=cliente)
    return render(request, 'clientes/form_cliente.html', {'form': form})

# 4. ASIGNACIÓN (Para que un usuario pueda asignar clientes a otros usuarios)
@requiere_rol('Administrador General')
def asignar_cliente(request):
    """Asocia un usuario del sistema con un cliente.

    Solo para el rol `Administrador General`.

    Args:
        request: Petición HTTP.

    Returns:
        HttpResponse: Formulario o redirección a `lista_clientes`.
    """
    if request.method == 'POST':
        form = AsignacionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_clientes')
    else:
        form = AsignacionForm()
    return render(request, 'clientes/form_asignacion.html', {'form': form})

@login_required
def convertirse_en_cliente(request):
    """Permite a un usuario registrarse a sí mismo como cliente persona física.

    Si el usuario ya tiene un cliente asociado, lo redirige a `mis_clientes`.
    Al guardar, crea el `Cliente` y su asociación `UsuarioCliente`.

    Args:
        request: Petición HTTP.

    Returns:
        HttpResponse: Formulario o redirección a `mis_clientes`.
    """
    # Si ya tiene no se permite
    if UsuarioCliente.objects.filter(usuario=request.user).exists():
        return redirect('mis_clientes') 

    if request.method == 'POST':
        form = ClienteFisicaForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.tipo_persona = Cliente.TipoPersona.FISICA
            cliente.save()
            UsuarioCliente.objects.create(usuario=request.user, cliente=cliente)
            return redirect('mis_clientes')
    else:
        form = ClienteFisicaForm(initial={
            'nombre_o_denominacion': f"{request.user.first_name} {request.user.last_name}".strip()
        })

    return render(request, 'clientes/convertirse_en_cliente.html', {'form': form})
