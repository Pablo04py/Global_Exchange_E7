from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.contrib import messages
from .models import Cliente, UsuarioCliente
from .forms import ClienteForm, AsignacionForm, ClienteFisicaForm
from usuarios.decorators import requiere_rol

@requiere_rol('Administrador General')
def lista_clientes(request):
    clientes = Cliente.objects.all() 
    return render(request, 'clientes/lista_clientes.html', {'clientes': clientes})  

@login_required
def mis_clientes(request):
    clientes = Cliente.objects.filter(usuarios_asociados__usuario=request.user)
    return render(request, 'clientes/mis_clientes.html', {'clientes': clientes})

@requiere_rol('Administrador General')
def crear_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save() 
            return redirect('lista_clientes')
    else:
        form = ClienteForm()
    return render(request, 'clientes/form_cliente.html', {'form': form})

@requiere_rol('Administrador General')
def editar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect('lista_clientes')
    else:
        form = ClienteForm(instance=cliente)
    return render(request, 'clientes/form_cliente.html', {'form': form})

@requiere_rol('Administrador General')
def asignar_cliente(request):
    if request.method == 'POST':
        form = AsignacionForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Asignación realizada exitosamente.")
                return redirect('lista_clientes')
            except ValidationError as e:
                form.add_error(None, e.message)
    else:
        form = AsignacionForm()
    return render(request, 'clientes/form_asignacion.html', {'form': form})

@login_required
def convertirse_en_cliente(request):
    # Solo bloquea si el usuario ya posee un perfil propio como Persona FÍSICA
    if UsuarioCliente.objects.filter(usuario=request.user, cliente__tipo_persona=Cliente.TipoPersona.FISICA).exists():
        messages.warning(request, "Ya posees un perfil registrado como Persona Física.")
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