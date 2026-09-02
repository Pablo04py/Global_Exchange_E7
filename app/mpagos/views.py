"""
Módulo de controladores/vistas para la gestión de Medios de Pago (mpagos).

Implementa la lógica del CRUD (Crear, Leer, Modificar, Eliminar) asegurando
que cada cliente acceda e interactúe únicamente con sus propios medios de pago.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import MedioPago
from .forms import MedioPagoForm


@login_required
def listar_medios_pago(request):
    """
    Vista para consultar y listar todos los medios de pago activos del usuario.

    Args:
        request (HttpRequest): Objeto de petición HTTP con la sesión del usuario.

    Returns:
        HttpResponse: Render de la plantilla mpagos/listar.html con el QuerySet de medios.
    """
    # Filtrado estricto por usuario autenticado y estado activo (borrado lógico)
    medios = MedioPago.objects.filter(usuario=request.user, activo=True)
    
    # Renderizado de la plantilla de listado pasando los objetos en contexto
    return render(request, 'mpagos/listar.html', {'medios': medios})


@login_required
def crear_medio_pago(request):
    """
    Vista para registrar un nuevo medio de pago asignado al usuario actual.

    Soporta procesamiento POST para guardado y GET para desplegar el formulario.

    Args:
        request (HttpRequest): Objeto de petición HTTP.

    Returns:
        HttpResponse: Redirección a la lista o render del formulario con mensajes de estado.
    """
    if request.method == 'POST':
        # Instanciar el formulario con los datos recibidos del usuario
        form = MedioPagoForm(request.POST)
        
        if form.is_valid():
            # Asignar la instancia sin guardar en BD para inyectar el usuario
            medio = form.save(commit=False)
            medio.usuario = request.user
            
            # Si el nuevo medio se marca como predeterminado, desmarcar los anteriores
            if medio.es_predeterminado:
                MedioPago.objects.filter(usuario=request.user).update(es_predeterminado=False)
                
            # Persistir finalmente en PostgreSQL
            medio.save()
            
            # Notificar al usuario mediante el framework de mensajes de Django
            messages.success(request, "Medio de pago registrado exitosamente.")
            return redirect('mpagos:listar')
    else:
        # Petición GET: Inicializar formulario vacío
        form = MedioPagoForm()

    return render(request, 'mpagos/form.html', {
        'form': form, 
        'titulo': 'Registrar Medio de Pago'
    })


@login_required
def eliminar_medio_pago(request, pk):
    """
    Vista para deshabilitar (borrado lógico) un medio de pago perteneciente al usuario.

    Args:
        request (HttpRequest): Objeto de petición HTTP.
        pk (int): Clave primaria (ID) del medio de pago a deshabilitar.

    Returns:
        HttpResponse: Redirección al listado o render de la pantalla de confirmación.
    """
    # Garantizar que el objeto exista y pertenezca exclusivamente al usuario en sesión
    medio = get_object_or_404(MedioPago, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        # Aplicar borrado lógico desmarcando la bandera activo
        medio.activo = False
        medio.save()
        
        messages.success(request, "Medio de pago eliminado correctamente.")
        return redirect('mpagos:listar')

    return render(request, 'mpagos/confirmar_eliminar.html', {'medio': medio})

@login_required
def editar_medio_pago(request, pk):
    """
    Vista para modificar los datos de un medio de pago existente del usuario.

    Carga los datos actuales en el formulario MedioPagoForm y procesa las
    modificaciones asegurando que solo el propietario pueda editarlos.

    Args:
        request (HttpRequest): Objeto de petición HTTP.
        pk (int): Identificador del medio de pago a editar.

    Returns:
        HttpResponse: Redirección al listado tras actualizar o render del formulario.
    """
    # Obtener la instancia garantizando que pertenezca al usuario en sesión
    medio = get_object_or_404(MedioPago, pk=pk, usuario=request.user, activo=True)

    if request.method == 'POST':
        # Vincular el formulario con la instancia existente y los datos recibidos
        form = MedioPagoForm(request.POST, instance=medio)
        
        if form.is_valid():
            # Obtener el objeto antes de persistir para evaluar banderas
            medio_editado = form.save(commit=False)
            
            # Si se marca como predeterminado, desmarcar los demás registros del usuario
            if medio_editado.es_predeterminado:
                MedioPago.objects.filter(usuario=request.user).exclude(pk=pk).update(es_predeterminado=False)
                
            # Persistir los cambios en la base de datos PostgreSQL
            medio_editado.save()
            
            # Notificar éxito al usuario
            messages.success(request, "Medio de pago actualizado correctamente.")
            return redirect('mpagos:listar')
    else:
        # Petición GET: Inicializar formulario precompletado con los datos del objeto
        form = MedioPagoForm(instance=medio)

    # Renderizar la plantilla reutilizando el formulario de mpagos
    return render(request, 'mpagos/form.html', {
        'form': form,
        'titulo': 'Editar Medio de Pago'
    })