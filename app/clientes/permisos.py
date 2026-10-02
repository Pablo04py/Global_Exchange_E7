from .models import Cliente, UsuarioCliente


def obtener_cliente_activo(request):
    """
    Obtiene el cliente actualmente seleccionado por el usuario.

    El identificador del cliente activo se obtiene de la sesión mediante
    ``ge_active_client``. Además, se verifica que el cliente esté realmente
    asociado al usuario autenticado para evitar acceso a clientes ajenos.

    Args:
        request:
            Solicitud HTTP de Django que contiene al usuario autenticado
            y los datos de sesión.

    Returns:
        Cliente | None:
            Instancia del cliente activo si existe y pertenece al usuario.
            Retorna ``None`` si el usuario no está autenticado, no existe
            un cliente seleccionado o el cliente no pertenece al usuario.
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
    Determina si el usuario posee el rol global Administrador General.

    La comprobación considera el override utilizado durante desarrollo,
    los grupos de Django, los roles sincronizados en el usuario local y,
    como respaldo, los roles presentes en el payload OIDC de Keycloak.

    Args:
        request:
            Solicitud HTTP de Django.

    Returns:
        bool:
            ``True`` si el usuario posee el rol Administrador General.
            ``False`` en caso contrario.
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
    Determina si el usuario puede administrar un cliente determinado.

    La administración puede realizarse de dos maneras:

    - mediante el rol global ``Administrador General``;
    - mediante una asociación ``UsuarioCliente`` con rol local ``ADMIN``.

    El rol local ADMIN pertenece únicamente al cliente asociado y no
    equivale al rol global Administrador General.

    Args:
        request:
            Solicitud HTTP de Django que contiene al usuario autenticado.

        cliente:
            Instancia de Cliente sobre la cual se verifican los permisos.

    Returns:
        bool:
            ``True`` si el usuario puede administrar el cliente.
            ``False`` si no posee los permisos necesarios.
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