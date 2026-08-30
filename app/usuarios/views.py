from django.shortcuts import render

from django.http import HttpResponse
from .decorators import requiere_rol


def perfil(request):
    if not request.user.is_authenticated:
        return HttpResponse("No estás logueado.")
    return HttpResponse(f"Hola {request.user.username}. Tus roles: {request.user.roles}")


@requiere_rol('Cajero')
def zona_cajero(request):
    return HttpResponse("Bienvenido, sos Cajero. Esta vista es exclusiva para ese rol.")
