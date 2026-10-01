from .models import Cliente, UsuarioCliente


def obtener_cliente_activo(request):
    """
    Obtiene el cliente activo verificando que esté
    asociado al usuario autenticado.
    """

    if not request.user.is_authenticated:
        return None

    cliente_id = request.session.get('ge_active_client')

    if not cliente_id:
        return None

    return (
        Cliente.objects
        .filter(
            id=cliente_id,
            usuarios_asociados__usuario=request.user
        )
        .first()
    )


def es_administrador_general(request):
    """
    Comprueba si el usuario posee el rol global
    Administrador General.
    """

    if not request.user.is_authenticated:
        return False

    # Override utilizado durante desarrollo
    if request.session.get('ge_role') == 'Administrador General':
        return True

    # Roles sincronizados como grupos Django
    if request.user.groups.filter(
        name='Administrador General'
    ).exists():
        return True

    # Roles guardados en el shadow user
    roles = getattr(request.user, 'roles', [])

    if 'Administrador General' in roles:
        return True

    # Fallback al payload OIDC
    payload = request.session.get(
        'oidc_access_token_payload',
        {}
    )

    realm_roles = (
        payload
        .get('realm_access', {})
        .get('roles', [])
    )

    return 'Administrador General' in realm_roles


def puede_administrar_cliente(request, cliente):
    """
    Un cliente puede ser administrado por:
    - Administrador General del sistema.
    - Usuario ADMIN de ese cliente.
    """

    if not request.user.is_authenticated or not cliente:
        return False

    if es_administrador_general(request):
        return True

    return UsuarioCliente.objects.filter(
        usuario=request.user,
        cliente=cliente,
        rol_cliente=UsuarioCliente.RolCliente.ADMIN
    ).exists()