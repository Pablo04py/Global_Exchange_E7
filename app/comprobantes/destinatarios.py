"""Email al que se envía la factura de una transacción (SCRUM-23).

La factura le llega al cliente que hizo la compra o venta, al email con el que
creó su cuenta. Lo usan tanto el Documento Electrónico de SCRUM-56 (`dEmailRec`,
al que Factura Segura envía el KuDE y el XML) como el envío propio de esta app.
"""

from clientes.models import UsuarioCliente


def _email_valido(usuario):
    """Email del usuario si está activo y lo tiene cargado.

    Args:
        usuario: Usuario del sistema.

    Returns:
        str: Email sin espacios, o cadena vacía.
    """
    if usuario is None or not usuario.is_active:
        return ''
    return (usuario.email or '').strip()


def email_receptor_factura(transaccion):
    """Email del cliente que hizo la operación, para recibir su factura.

    1. Si quien operó es un usuario asociado al cliente (compra web con su
       cuenta), se usa su email.
    2. Si no (en caja, quien operó es el cajero), se usa el email de la cuenta
       del cliente: el usuario asociado activo con email, primero el de rol
       `ADMIN` y si no el de asociación más antigua.
    3. Si el cliente no tiene ninguna cuenta con email, se usa el del usuario
       de la transacción (comportamiento original de SCRUM-56).

    Args:
        transaccion: Transacción facturada.

    Returns:
        str: Email del receptor, o cadena vacía si no hay ninguno.
    """
    usuario = transaccion.usuario
    asociados = UsuarioCliente.objects.filter(cliente_id=transaccion.cliente_id).select_related('usuario')

    if asociados.filter(usuario_id=usuario.pk).exists():
        email = _email_valido(usuario)
        if email:
            return email

    ordenados = sorted(
        asociados,
        key=lambda uc: (uc.rol_cliente != UsuarioCliente.RolCliente.ADMIN, uc.fecha_asociacion),
    )
    for asociacion in ordenados:
        email = _email_valido(asociacion.usuario)
        if email:
            return email

    return (usuario.email or '').strip()
