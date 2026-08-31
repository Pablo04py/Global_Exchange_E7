MENU_BY_ROLE = {

    "Administrador General": [
        {
            "label": None,
            "items": [
                {"name": "Dashboard",       "url": "/dashboard/",    "icon": "ti-layout-dashboard"},
            ]
        },
        {
            "label": "Operaciones",
            "items": [
                {"name": "Transacciones",   "url": "/transacciones/","icon": "ti-arrows-right-left"},
                {"name": "Cotizaciones",    "url": "/cotizaciones/", "icon": "ti-chart-line"},
                {"name": "Cajas",           "url": "/cajas/",        "icon": "ti-cash-register"},
            ]
        },
        {
            "label": "Gestión",
            "items": [
                {"name": "Clientes",        "url": "/clientes/",     "icon": "ti-users"},
                {"name": "Usuarios",        "url": "/usuarios/",     "icon": "ti-user-cog"},
                {"name": "Sucursales",      "url": "/sucursales/",   "icon": "ti-building-store"},
            ]
        },
        {
            "label": "Finanzas",
            "items": [
                {"name": "Facturación",     "url": "/facturas/",     "icon": "ti-file-invoice"},
                {"name": "Ganancias",       "url": "/ganancias/",    "icon": "ti-trending-up"},
                {"name": "Reportes",        "url": "/reportes/",     "icon": "ti-report-analytics"},
            ]
        },
        {
            "label": "Sistema",
            "items": [
                {"name": "Configuración",   "url": "/configuracion/","icon": "ti-settings"},
                {"name": "Auditoría",       "url": "/auditoria/",    "icon": "ti-shield-check"},
                {"name": "Monedas",         "url": "/monedas/",      "icon": "ti-currency-dollar"},
            ]
        },
    ],

    "Analista Cambiario": [
        {
            "label": None,
            "items": [
                {"name": "Dashboard",       "url": "/dashboard/",    "icon": "ti-layout-dashboard"},
            ]
        },
        {
            "label": "Mercado",
            "items": [
                {"name": "Cotizaciones",    "url": "/cotizaciones/", "icon": "ti-chart-line"},
                {"name": "Tasas de Cambio", "url": "/tasas/",        "icon": "ti-adjustments-horizontal"},
                {"name": "Ganancias",       "url": "/ganancias/",    "icon": "ti-trending-up"},
            ]
        },
        {
            "label": "Reportes",
            "items": [
                {"name": "Transacciones",   "url": "/transacciones/","icon": "ti-arrows-right-left"},
                {"name": "Facturación",     "url": "/facturas/",     "icon": "ti-file-invoice"},
                {"name": "Reportes",        "url": "/reportes/",     "icon": "ti-report-analytics"},
            ]
        },
    ],

    "Cajero": [
        {
            "label": None,
            "items": [
                {"name": "Dashboard",       "url": "/dashboard/",    "icon": "ti-layout-dashboard"},
            ]
        },
        {
            "label": "Mi Caja",
            "items": [
                {"name": "Apertura de Caja","url": "/caja/apertura/","icon": "ti-lock-open"},
                {"name": "Cierre de Caja",  "url": "/caja/cierre/",  "icon": "ti-lock"},
                {"name": "Stock de Divisas","url": "/caja/stock/",   "icon": "ti-wallet"},
                {"name": "Movimientos",     "url": "/caja/movimientos/","icon": "ti-list-details"},
            ]
        },
        {
            "label": "Operaciones",
            "items": [
                {"name": "Transacciones",   "url": "/transacciones/","icon": "ti-arrows-right-left"},
                {"name": "Cotizaciones",    "url": "/cotizaciones/", "icon": "ti-chart-line"},
            ]
        },
    ],

    "Cliente": [
        {
            "label": None,
            "items": [
                {"name": "Inicio",          "url": "/cliente/",      "icon": "ti-home"},
            ]
        },
        {
            "label": "Operar",
            "items": [
                {"name": "Cotizaciones",    "url": "/cotizaciones/", "icon": "ti-chart-line"},
                {"name": "Comprar Divisas", "url": "/operar/compra/","icon": "ti-arrow-down-circle"},
                {"name": "Vender Divisas",  "url": "/operar/venta/", "icon": "ti-arrow-up-circle"},
            ]
        },
        {
            "label": "Mi cuenta",
            "items": [
                {"name": "Mis Transacciones","url": "/mis-transacciones/","icon": "ti-history"},
                {"name": "Mis Facturas",    "url": "/mis-facturas/", "icon": "ti-file-invoice"},
            ]
        },
    ],

    "Sin Rol": [
        {
            "label": None,
            "items": [
                {"name": "Cotizaciones",    "url": "/cotizaciones/", "icon": "ti-chart-line"},
            ]
        },
    ],
}

ROLE_LABELS = {
    "Administrador General": "Administrador General",
    "Analista Cambiario":    "Analista Cambiario",
    "Cajero":                "Cajero",
    "Cliente":               "Cliente",
    "Sin Rol":               "Sin rol asignado",
}


def menu_context(request):
    if not request.user.is_authenticated:
        return {
            "menu_sections": [],
            "user_role": None,
            "user_role_label": None,
        }

    # Leer rol desde el token OIDC (cuando Keycloak esté integrado)
    role = None
    oidc_payload = request.session.get('oidc_access_token_payload', {})
    realm_roles  = oidc_payload.get('realm_access', {}).get('roles', [])

    for r in ["Administrador General", "Analista Cambiario", "Cajero", "Cliente"]:
        if r in realm_roles:
            role = r
            break

    # Fallback para desarrollo: rol manual desde session
    if not role:
        role = request.session.get('ge_role', 'Sin Rol')

    # Superuser de Django → Administrador General
    if request.user.is_superuser and not role:
        role = "Administrador General"

    menu_sections = MENU_BY_ROLE.get(role, MENU_BY_ROLE["Sin Rol"])

    return {
        "menu_sections":  menu_sections,
        "user_role":      role,
        "user_role_label": ROLE_LABELS.get(role, role),
    }