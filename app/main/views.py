"""
Controladores y Vistas (Views) para el panel principal y Dashboard.

Contiene las funciones auxiliares para resolver roles de Keycloak,
generación del menú lateral adaptativo y endpoints de interacción con la sesión.
"""

import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.conf import settings as django_settings
from django.urls import reverse 

from clientes.models import Cliente

# Mapeo de slugs utilizados en la URL de desarrollo -> etiqueta interna de rol
ROLE_SLUGS = {
    "admin": "Administrador General",
    "analista": "Analista Cambiario",
    "cajero": "Cajero",
    "sinrol": "Sin Rol",
}

# Orden de prioridad para resolver el rol principal cuando Keycloak devuelve múltiples roles
ROLE_PRIORITY = ["Administrador General", "Analista Cambiario", "Cajero"]


def resolve_keycloak_role(user_roles):
    """
    Determina la etiqueta del rol principal con base en la lista de roles del usuario.

    Args:
        user_roles (list): Lista de nombres de roles asignados al usuario.

    Returns:
        str: Nombre del rol principal priorizado o 'Sin Rol' si no se encuentra coincidencia.
    """
    if not user_roles:
        return "Sin Rol"
    # Recorre la lista según el orden de jerarquía definido
    for role in ROLE_PRIORITY:
        if role in user_roles:
            return role
    return "Sin Rol"


def get_menu_sections(role, active_client, is_authenticated=False):
    """
    Construye de forma dinámica las secciones del menú lateral según el estado
    de autenticación, el rol del usuario y el cliente actualmente activo.

    Args:
        role (str): Rol operativo del usuario ('Administrador General', 'Cajero', etc.).
        active_client (dict|None): Información del cliente activo en sesión.
        is_authenticated (bool): Indica si el usuario ha iniciado sesión.

    Returns:
        list: Estructura de listas y diccionarios con las secciones y links del menú.
    """
    # 1. Menú para Visitantes Públicos (Usuarios sin sesión activa)
    if not is_authenticated:
        return [
            {
                "label": "Mesa Pública",
                "items": [
                    {"name": "Inicio", "url": "/", "icon": "ti-home"},
                    {"name": "Cotizaciones en Vivo", "url": "/cotizaciones/", "icon": "ti-trending-up"},
                    {"name": "Simulador de Cambio", "url": "/calculadora/", "icon": "ti-calculator"},
                ]
            },
            {
                "label": "Información",
                "items": [
                    {"name": "Nuestras Sucursales", "url": "/sucursales/", "icon": "ti-map-pin"},
                    {"name": "Preguntas Frecuentes", "url": "/faq/", "icon": "ti-help"},
                    {"name": "Contacto", "url": "/contacto/", "icon": "ti-headset"},
                ]
            }
        ]

    # 2. Menú para Usuarios Registrados en estado de verificación ("Sin Rol")
    if role == "Sin Rol":
        return [
            {
                "label": "General",
                "items": [
                    {"name": "Inicio", "url": "/dashboard/", "icon": "ti-layout-dashboard"},
                    {"name": "Cotizaciones", "url": "/cotizaciones/", "icon": "ti-trending-up"},
                ]
            },
            {
                "label": "Mi Cuenta",
                "items": [
                    {"name": "Estado de Verificación", "url": "/cuenta/verificacion/", "icon": "ti-id-badge-2", "badge": "Pendiente"},
                    {"name": "Mi Perfil", "url": "/cuenta/perfil/", "icon": "ti-user-circle"},
                ]
            }
        ]

    # 3. Menú base para Usuarios autenticados con Rol Operativo
    sections = [
        {
            "label": "General",
            "items": [
                {"name": "Dashboard", "url": "/dashboard/", "icon": "ti-layout-dashboard"},
                {"name": "Cotizaciones y Gráficos", "url": "/cotizaciones/", "icon": "ti-trending-up"},
            ]
        },
        {
            "label": "Mi Gestión",
            "items": [
                {"name": "Mis Clientes", "url": reverse("mis_clientes"), "icon": "ti-address-book"},
            ]
        }
    ]

    # Módulo de operaciones activables con cliente seleccionado
    sections.append({
        "label": "Operativa",
        "items": [
            {"name": "Mis Clientes", "url": reverse("mis_clientes"), "icon": "ti-address-book"},
            {"name": "Operar / Cambiar Divisas", "url": "/operar/", "icon": "ti-arrows-exchange"},
            {"name": "Historial de Operaciones", "url": "/historial/", "icon": "ti-history"},
            {"name": "Facturas DNIT", "url": "/facturas/", "icon": "ti-receipt"},
        ]
    })

    # Opciones de menú específicas para el rol Cajero
    if role == "Cajero":
        sections.append({
            "label": "Gestión de Caja",
            "items": [
                {"name": "Apertura / Cierre", "url": "/caja/gestion/", "icon": "ti-cash-register"},
                {"name": "Movimientos de Efectivo", "url": "/caja/movimientos/", "icon": "ti-file-spreadsheet"},
            ]
        })

    # Opciones de menú específicas para el rol Analista Cambiario
    if role == "Analista Cambiario":
        sections.append({
            "label": "Análisis Cambiario",
            "items": [
                {"name": "Ajuste de Tasas", "url": "/tasas/ajuste/", "icon": "ti-currency-dollar"},
                {"name": "Monitoreo de Ganancias", "url": "/ganancias/", "icon": "ti-chart-bar"},
            ]
        })

    # Opciones de menú específicas para el rol Administrador General
    if role == "Administrador General":
        sections.append({
            "label": "Administración",
            "items": [
                {"name": "Clientes", "url": reverse("lista_clientes"), "icon": "ti-users"},
                {"name": "Nuevo Cliente", "url": reverse("crear_cliente"), "icon": "ti-user-plus"},
                {"name": "Asignar Cliente", "url": reverse("asignar_cliente"), "icon": "ti-link"},
                {"name": "Parámetros del Sistema", "url": "/admin/parametros/", "icon": "ti-settings"},
                {"name": "Auditoría de Logs", "url": "/admin/auditoria/", "icon": "ti-shield-check"},
            ]
        })

    return sections


def dashboard(request):
    """
    Vista principal del Dashboard.

    Sincroniza el rol activo, los clientes asociados del usuario,
    el cliente activo seleccionado en la sesión y prepara las tarjetas métricas (summary cards).

    Args:
        request: Objeto HttpRequest.

    Returns:
        HttpResponse: Renderiza el template 'dashboard.html'.
    """
    is_auth = request.user.is_authenticated

    if is_auth:
        # Prioridad 1: Override manual en desarrollo mediante variable de sesión
        role = request.session.get('ge_role')
        if not role:
            # Prioridad 2: Extraer roles asignados mediante los Grupos de Django
            user_roles = list(request.user.groups.values_list('name', flat=True))
            
            # Prioridad 3: Fallback al payload del token OIDC en la sesión
            if not user_roles:
                oidc_payload = request.session.get('oidc_access_token_payload', {})
                user_roles = oidc_payload.get('realm_access', {}).get('roles', [])

            role = resolve_keycloak_role(user_roles)
    else:
        role = None

    associated_clients = []
    if is_auth:
        # Consultar la base de datos para obtener los clientes vinculados al usuario
        clientes_qs = Cliente.objects.filter(usuarios_asociados__usuario=request.user)
        associated_clients = [
            {
                "id": str(c.id),
                "name": c.nombre_o_denominacion,
                "category": c.get_categoria_display(),
            }
            for c in clientes_qs
        ]

    # Validación del cliente activo guardado en la sesión
    active_client_id = request.session.get('ge_active_client')
    valid_ids = [c['id'] for c in associated_clients]

    # Asigna por defecto el primer cliente si no hay uno seleccionado o el que está expiró
    if (not active_client_id or active_client_id not in valid_ids) and associated_clients:
        active_client_id = associated_clients[0]['id']
        request.session['ge_active_client'] = active_client_id

    # Obtiene los datos del cliente activo actual
    active_client = next((c for c in associated_clients if c['id'] == active_client_id), None)

    # Definición de tarjetas dinámicas del Dashboard según el rol del usuario
    cards_by_role = {
        "Administrador General": [
            {"label": "Transacciones hoy", "value": "142", "sub": "+12% vs ayer", "icon": "ti-arrows-right-left", "bg": "#DBEAFE", "color": "#2563EB"},
            {"label": "Clientes activos", "value": str(len(associated_clients)), "sub": "8 nuevos esta semana", "icon": "ti-users", "bg": "#D1FAE5", "color": "#059669"},
            {"label": "Ganancia del día", "value": "G. 4,2M", "sub": "en 3 monedas", "icon": "ti-trending-up", "bg": "#FEF3C7", "color": "#D97706"},
            {"label": "Cajas abiertas", "value": "6 / 8", "sub": "2 pendientes", "icon": "ti-cash-register", "bg": "#EDE9FE", "color": "#7C3AED"},
        ],
        "Analista Cambiario": [
            {"label": "Tasa USD/PYG", "value": "7.620", "sub": "Actualizada hace 3min", "icon": "ti-currency-dollar", "bg": "#DBEAFE", "color": "#2563EB"},
            {"label": "Tasa EUR/PYG", "value": "8.310", "sub": "Actualizada hace 3min", "icon": "ti-currency-euro", "bg": "#D1FAE5", "color": "#059669"},
            {"label": "Clientes vinculados", "value": str(len(associated_clients)), "sub": "Cuentas asociadas", "icon": "ti-address-book", "bg": "#FEF3C7", "color": "#D97706"},
            {"label": "Transacciones", "value": "142", "sub": "Procesadas hoy", "icon": "ti-arrows-right-left", "bg": "#EDE9FE", "color": "#7C3AED"},
        ],
        "Cajero": [
            {"label": "Mi caja", "value": "Abierta", "sub": "Desde las 08:00", "icon": "ti-lock-open", "bg": "#D1FAE5", "color": "#059669"},
            {"label": "Stock USD", "value": "$ 12.400", "sub": "En caja", "icon": "ti-currency-dollar", "bg": "#DBEAFE", "color": "#2563EB"},
            {"label": "Transacciones", "value": "38", "sub": "En tu turno", "icon": "ti-arrows-right-left", "bg": "#FEF3C7", "color": "#D97706"},
            {"label": "Diferencia", "value": "G. 0", "sub": "Sin discrepancias", "icon": "ti-check", "bg": "#D1FAE5", "color": "#059669"},
            {"label": "Clientes vinculados", "value": str(len(associated_clients)), "sub": "En tu cuenta", "icon": "ti-address-book", "bg": "#D1FAE5", "color": "#059669"},
        ],
        "Sin Rol": [],
    }

    context = {
        "summary_cards": cards_by_role.get(role, []) if is_auth else [],
        "user_role": role,
        "user_role_label": role if is_auth else "Visitante",
        "menu_sections": get_menu_sections(role, active_client, is_authenticated=is_auth),
        "associated_clients": associated_clients,
        "active_client": active_client,
    }

    return render(request, 'dashboard.html', context)


@login_required
def select_client(request):
    """
    Endpoint AJAX para cambiar el cliente activo dentro de la sesión HTTP.

    Args:
        request: Objeto HttpRequest con el payload JSON en el cuerpo.

    Returns:
        JsonResponse: Estado de la operación (200 OK, 403 Forbidden o 400 Bad Request).
    """
    if request.method == "POST":
        data = json.loads(request.body)
        client_id = data.get("client_id")
        
        # Verifica que el usuario tenga acceso al cliente que intenta seleccionar
        if Cliente.objects.filter(id=client_id, usuarios_asociados__usuario=request.user).exists():
            request.session['ge_active_client'] = client_id
            return JsonResponse({"status": "ok"})
            
        return JsonResponse({"status": "forbidden", "message": "No tiene permisos sobre este cliente"}, status=403)
        
    return JsonResponse({"status": "error"}, status=400)


def set_role(request, role):
    """
    Vista de utilidad para simular el cambio de rol manualmente en entorno de desarrollo.

    Args:
        request: Objeto HttpRequest.
        role (str): Slug del rol a simular ('admin', 'cajero', 'analista', 'sinrol').

    Returns:
        HttpResponse: Redirección al dashboard o error 403 en caso de estar en producción.
    """
    # Restringe esta herramienta exclusivamente si DEBUG=True
    if not django_settings.DEBUG:
        return HttpResponseForbidden()

    internal_role = ROLE_SLUGS.get(role)
    if internal_role:
        request.session['ge_role'] = internal_role
        
    return redirect(request.GET.get('next', '/dashboard/'))