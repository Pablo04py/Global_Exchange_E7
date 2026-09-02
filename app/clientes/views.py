"""
Controladores y Vistas (Views) para el módulo de Clientes.

Gestiona las peticiones HTTP, el control de acceso según roles, y
el procesamiento de los formularios de la aplicación.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.contrib import messages
from .models import Cliente, UsuarioCliente
from .forms import ClienteForm, AsignacionForm, ClienteFisicaForm
from usuarios.decorators import requiere_rol


@requiere_rol('Administrador General')
def lista_clientes(request):
    """
    Muestra el listado completo de clientes cargados en el sistema.

    Acceso restringido únicamente a usuarios con el rol 'Administrador General'.

    Args:
        request: Objeto HttpRequest.

    Returns:
        HttpResponse: Renderiza el template 'clientes/lista_clientes.html'.
    """
    # Obtiene todos los clientes registrados
    clientes = Cliente.objects.all() 
    return render(request, 'clientes/lista_clientes.html', {'clientes': clientes})  


@login_required
def mis_clientes(request):
    """
    Muestra la lista de cuentas/empresas asociadas al usuario autenticado.

    Args:
        request: Objeto HttpRequest con el usuario en sesión.

    Returns:
        HttpResponse: Renderiza 'clientes/mis_clientes.html' con sus cuentas.
    """
    # Filtra solo los clientes vinculados al usuario actual en la tabla intermedia
    clientes = Cliente.objects.filter(usuarios_asociados__usuario=request.user)
    return render(request, 'clientes/mis_clientes.html', {'clientes': clientes})


@requiere_rol('Administrador General')
def crear_cliente(request):
    """
    Permite a un administrador registrar manualmente un nuevo cliente.

    Args:
        request: Objeto HttpRequest.

    Returns:
        HttpResponse: Formulario 'clientes/form_cliente.html' o redirección a la lista.
    """
    if request.method == 'POST':
        # Procesamiento del formulario enviado
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save() 
            return redirect('lista_clientes')
    else:
        # Carga del formulario vacío en solicitudes GET
        form = ClienteForm()
    return render(request, 'clientes/form_cliente.html', {'form': form})


@requiere_rol('Administrador General')
def editar_cliente(request, cliente_id):
    """
    Permite modificar los datos de un cliente existente.

    Args:
        request: Objeto HttpRequest.
        cliente_id (UUID): Identificador único del cliente a modificar.

    Returns:
        HttpResponse: Formulario con los datos cargados o redirección a la lista.
    """
    # Obtiene el cliente o lanza un error HTTP 404 si el ID no existe
    cliente = get_object_or_404(Cliente, id=cliente_id)
    
    if request.method == 'POST':
        # Se envía la instancia para sobrescribir los datos del cliente
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect('lista_clientes')
    else:
        # Carga inicial del formulario con los datos guardados en BD
        form = ClienteForm(instance=cliente)
    return render(request, 'clientes/form_cliente.html', {'form': form})


@requiere_rol('Administrador General')
def asignar_cliente(request):
    """
    Permite asociar un usuario a un cliente desde la interfaz de administración.

    Atrapa las excepciones de reglas de negocio (`ValidationError`) y las muestra
    como un mensaje de error dentro del formulario.

    Args:
        request: Objeto HttpRequest.

    Returns:
        HttpResponse: Renderiza el formulario 'clientes/form_asignacion.html'.
    """
    if request.method == 'POST':
        form = AsignacionForm(request.POST)
        if form.is_valid():
            try:
                # Intenta guardar el nuevo vínculo
                form.save()
                messages.success(request, "Asignación realizada exitosamente.")
                return redirect('lista_clientes')
            except ValidationError as e:
                # Captura el error de la regla 1:1 de Persona Física y evita el HTTP 500
                form.add_error(None, e.message)
    else:
        form = AsignacionForm()
    return render(request, 'clientes/form_asignacion.html', {'form': form})


@login_required
def convertirse_en_cliente(request):
    """
    Permite que un usuario autenticado registre su perfil de Persona Física.

    Regla Multicliente:
    Si el usuario ya tiene un perfil de Persona Física registrado, es redirigido
    impidiendo la duplicación. Si administra empresas pero no tiene perfil personal,
    se le permite continuar.

    Args:
        request: Objeto HttpRequest.

    Returns:
        HttpResponse: Renderiza 'clientes/convertirse_en_cliente.html'.
    """
    # Bloquea únicamente si ya tiene un perfil personal (Persona Física) creado
    if UsuarioCliente.objects.filter(usuario=request.user, cliente__tipo_persona=Cliente.TipoPersona.FISICA).exists():
        messages.warning(request, "Ya posees un perfil registrado como Persona Física.")
        return redirect('mis_clientes') 

    if request.method == 'POST':
        form = ClienteFisicaForm(request.POST)
        if form.is_valid():
            # Prepara la instancia sin guardar en la BD todavía
            cliente = form.save(commit=False)
            cliente.tipo_persona = Cliente.TipoPersona.FISICA # Asigna forzosamente FISICA
            cliente.save()
            
            # Asocia automáticamente al usuario autenticado con la cuenta recién creada
            UsuarioCliente.objects.create(usuario=request.user, cliente=cliente)
            return redirect('mis_clientes')
    else:
        # Precompleta el formulario usando los datos del usuario logueado
        form = ClienteFisicaForm(initial={
            'nombre_o_denominacion': f"{request.user.first_name} {request.user.last_name}".strip()
        })

    return render(request, 'clientes/convertirse_en_cliente.html', {'form': form})