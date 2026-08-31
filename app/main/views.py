import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.conf import settings as django_settings


def get_menu_sections(role, active_client, is_authenticated=False):
    """Genera las secciones del menú lateral según autenticación, rol y cliente activo"""

    # 1. Menú para Visitantes Públicos (Sin autenticar)
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

    # 2. Menú para Usuarios Registrados pero "Sin Rol" (En Verificación)
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

    # 3. Menú base para Usuarios con Rol Operativo
    sections = [
        {
            "label": "General",
            "items": [
                {"name": "Dashboard", "url": "/dashboard/", "icon": "ti-layout-dashboard"},
                {"name": "Cotizaciones y Gráficos", "url": "/cotizaciones/", "icon": "ti-trending-up"},
            ]
        }
    ]

    # RF13, RF15, RF23, RF41: Solo si el usuario tiene un cliente activo seleccionado
    if role == "Cliente" and active_client:
        sections.append({
            "label": "Operativa",
            "items": [
                {"name": "Operar / Cambiar Divisas", "url": "/operar/", "icon": "ti-arrows-exchange"},
                {"name": "Historial de Operaciones", "url": "/historial/", "icon": "ti-history"},
                {"name": "Facturas DNIT", "url": "/facturas/", "icon": "ti-receipt"},
            ]
        })

    # RF30-RF35: Funciones del Cajero
    if role == "Cajero":
        sections.append({
            "label": "Gestión de Caja",
            "items": [
                {"name": "Apertura / Cierre", "url": "/caja/gestion/", "icon": "ti-cash-register"},
                {"name": "Movimientos de Efectivo", "url": "/caja/movimientos/", "icon": "ti-file-spreadsheet"},
            ]
        })

    # RF10, RF42-RF44, RF47: Funciones del Analista Cambiario
    if role == "Analista Cambiario":
        sections.append({
            "label": "Análisis Cambiario",
            "items": [
                {"name": "Ajuste de Tasas", "url": "/tasas/ajuste/", "icon": "ti-currency-dollar"},
                {"name": "Monitoreo de Ganancias", "url": "/ganancias/", "icon": "ti-chart-bar"},
            ]
        })

    # RF7, RF11, RF46-RF48: Funciones de Administración
    if role == "Administrador General":
        sections.append({
            "label": "Administración",
            "items": [
                {"name": "Usuarios y Clientes", "url": "/admin/usuarios/", "icon": "ti-users"},
                {"name": "Parámetros del Sistema", "url": "/admin/parametros/", "icon": "ti-settings"},
                {"name": "Auditoría de Logs", "url": "/admin/auditoria/", "icon": "ti-shield-check"},
            ]
        })

    return sections


def dashboard(request):
    is_auth = request.user.is_authenticated
    role = request.session.get('ge_role', 'Sin Rol') if is_auth else None

    # Datos simulados de clientes asociados al usuario (RF4, RF9, RF26)
    mock_clients = [
        {"id": "c1", "name": "Juan Pérez (Personal)", "category": "Minorista"},
        {"id": "c2", "name": "Empresa S.A.", "category": "Corporativo"},
    ] if (is_auth and role == "Cliente") else []

    active_client_id = request.session.get('ge_active_client', mock_clients[0]['id'] if mock_clients else None)
    active_client = next((c for c in mock_clients if c['id'] == active_client_id), None)

    cards_by_role = {
        "Administrador General": [
            {"label": "Transacciones hoy", "value": "142",     "sub": "+12% vs ayer",          "icon": "ti-arrows-right-left", "bg": "#DBEAFE", "color": "#2563EB"},
            {"label": "Clientes activos",  "value": "1.284",   "sub": "8 nuevos esta semana",  "icon": "ti-users",             "bg": "#D1FAE5", "color": "#059669"},
            {"label": "Ganancia del día",  "value": "G. 4,2M", "sub": "en 3 monedas",          "icon": "ti-trending-up",       "bg": "#FEF3C7", "color": "#D97706"},
            {"label": "Cajas abiertas",    "value": "6 / 8",   "sub": "2 pendientes",          "icon": "ti-cash-register",     "bg": "#EDE9FE", "color": "#7C3AED"},
        ],
        "Analista Cambiario": [
            {"label": "Tasa USD/PYG",      "value": "7.620",   "sub": "Actualizada hace 3min", "icon": "ti-currency-dollar",   "bg": "#DBEAFE", "color": "#2563EB"},
            {"label": "Tasa EUR/PYG",      "value": "8.310",   "sub": "Actualizada hace 3min", "icon": "ti-currency-euro",     "bg": "#D1FAE5", "color": "#059669"},
            {"label": "Ganancia del día",  "value": "G. 4,2M", "sub": "en 3 monedas",          "icon": "ti-trending-up",       "bg": "#FEF3C7", "color": "#D97706"},
            {"label": "Transacciones",     "value": "142",     "sub": "Procesadas hoy",        "icon": "ti-arrows-right-left", "bg": "#EDE9FE", "color": "#7C3AED"},
        ],
        "Cajero": [
            {"label": "Mi caja",           "value": "Abierta", "sub": "Desde las 08:00",       "icon": "ti-lock-open",         "bg": "#D1FAE5", "color": "#059669"},
            {"label": "Stock USD",         "value": "$ 12.400","sub": "En caja",               "icon": "ti-currency-dollar",   "bg": "#DBEAFE", "color": "#2563EB"},
            {"label": "Transacciones",     "value": "38",      "sub": "En tu turno",           "icon": "ti-arrows-right-left", "bg": "#FEF3C7", "color": "#D97706"},
            {"label": "Diferencia",        "value": "G. 0",    "sub": "Sin discrepancias",     "icon": "ti-check",             "bg": "#D1FAE5", "color": "#059669"},
        ],
        "Cliente": [
            {"label": "Mis operaciones",   "value": "24",      "sub": "Este mes",              "icon": "ti-history",           "bg": "#DBEAFE", "color": "#2563EB"},
            {"label": "USD/PYG hoy",       "value": "7.620",   "sub": "Tasa de venta",         "icon": "ti-currency-dollar",   "bg": "#D1FAE5", "color": "#059669"},
            {"label": "Última operación",  "value": "$ 500",   "sub": "hace 2 días",           "icon": "ti-arrows-right-left", "bg": "#FEF3C7", "color": "#D97706"},
        ],
        "Sin Rol": [],
    }

    context = {
        "summary_cards": cards_by_role.get(role, []) if is_auth else [],
        "user_role": role,
        "user_role_label": role if is_auth else "Visitante",
        "menu_sections": get_menu_sections(role, active_client, is_authenticated=is_auth),
        "associated_clients": mock_clients,
        "active_client": active_client,
    }

    return render(request, 'dashboard.html', context)


# Endpoint AJAX para cambiar de cliente activo (RF9)
@login_required
def select_client(request):
    if request.method == "POST":
        data = json.loads(request.body)
        client_id = data.get("client_id")
        request.session['ge_active_client'] = client_id
        return JsonResponse({"status": "ok"})
    return JsonResponse({"status": "error"}, status=400)


# Solo para desarrollo — simular roles sin Keycloak
def set_role(request, role):
    if not django_settings.DEBUG:
        return HttpResponseForbidden()

    valid_roles = ["Administrador General", "Analista Cambiario", "Cajero", "Cliente", "Sin Rol"]
    if role in valid_roles:
        request.session['ge_role'] = role
    return redirect(request.GET.get('next', '/dashboard/'))