"""
Vistas y controladores del módulo de Usuarios.

Maneja la consulta del perfil personal y áreas con permisos restringidos.
"""

from django.shortcuts import render
from django.http import HttpResponse
from .decorators import requiere_rol


def perfil(request):
    """
    Muestra la información de sesión y la lista de roles del usuario autenticado.

    Args:
        request: Objeto HttpRequest.

    Returns:
        HttpResponse: Respuesta de texto con el nombre del usuario y sus roles.
    """
    # Verificación de inicio de sesión previa
    if not request.user.is_authenticated:
        return HttpResponse("No estás logueado.")
    
    # Retorna un saludo simple con la lista de roles leída del modelo
    return HttpResponse(f"Hola {request.user.username}. Tus roles: {request.user.roles}")


@requiere_rol('Cajero')
def zona_cajero(request):
    """
    Vista exclusiva para usuarios con el rol de 'Cajero'.

    Args:
        request: Objeto HttpRequest.

    Returns:
        HttpResponse: Mensaje de bienvenida para la interfaz de caja.
    """
    # Si pasa el decorador @requiere_rol, responde con la vista autorizada
    return HttpResponse("Bienvenido, sos Cajero. Esta vista es exclusiva para ese rol.")