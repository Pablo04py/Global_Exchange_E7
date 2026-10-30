from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone

from clientes.models import Cliente
from operaciones.models import Transaccion


MONEDA_FACTURA = 'PYG'


def decimal_a_texto(valor):
    """
    Convierte valores Decimal a texto sin notación científica.
    """
    if not isinstance(valor, Decimal):
        valor = Decimal(str(valor))

    return format(valor, 'f')


def obtener_monto_factura(transaccion):
    """
    Obtiene el monto total de la operación que será facturado en PYG.

    COMPRA:
        El cliente entrega PYG y recibe divisa.
        Se factura el monto entregado en PYG.

    VENTA:
        El cliente entrega divisa y recibe PYG luego de la comisión.
        Se factura el monto recibido en PYG.
    """

    if transaccion.tipo == Transaccion.Tipo.COMPRA:
        return transaccion.monto_pagado

    if transaccion.tipo == Transaccion.Tipo.VENTA:
        return transaccion.monto_recibido

    raise ValidationError(
        'Tipo de transacción no soportado para facturación.'
    )


def obtener_tipo_transaccion_sifen(transaccion):
    """
    Devuelve iTipTra visto desde Global Exchange, que es el emisor.
    """

    if transaccion.tipo == Transaccion.Tipo.COMPRA:
        # El cliente compra divisa.
        # Global Exchange vende divisa.
        return '5'

    if transaccion.tipo == Transaccion.Tipo.VENTA:
        # El cliente vende divisa.
        # Global Exchange compra divisa.
        return '6'

    raise ValidationError(
        'Tipo de transacción no soportado.'
    )


def obtener_descripcion_operacion(transaccion):
    """
    Descripción vista desde el emisor Global Exchange.
    """

    if transaccion.tipo == Transaccion.Tipo.COMPRA:
        return f'Venta de divisas {transaccion.moneda.codigo}'

    if transaccion.tipo == Transaccion.Tipo.VENTA:
        return f'Compra de divisas {transaccion.moneda.codigo}'

    raise ValidationError(
        'Tipo de transacción no soportado.'
    )


def obtener_codigo_item(transaccion):
    if transaccion.tipo == Transaccion.Tipo.COMPRA:
        prefijo = 'VD'
    elif transaccion.tipo == Transaccion.Tipo.VENTA:
        prefijo = 'CD'
    else:
        raise ValidationError(
            'Tipo de transacción no soportado.'
        )

    return f'GE-{prefijo}-{transaccion.moneda.codigo}'


def obtener_indicador_presencia(transaccion):
    """
    1 = Operación presencial
    2 = Operación electrónica
    """

    if transaccion.canal == Transaccion.Canal.CAJA:
        return '1'

    return '2'


def obtener_tipo_pago(transaccion):
    """
    Mapeo entre medios de pago de Global Exchange y SIFEN.
    """

    tipos = {
        'EFECTIVO': '1',
        'SIPAP': '5',

        # El modelo actual no diferencia tarjeta de crédito/débito.
        # Como Stripe procesa el pago electrónicamente,
        # utilizamos Pago Electrónico.
        'TARJETA': '21',
    }

    tipo = transaccion.medio_pago.tipo

    if tipo not in tipos:
        raise ValidationError(
            f'Medio de pago no soportado para facturación: {tipo}.'
        )

    return tipos[tipo]


def construir_receptor(transaccion):
    """
    Construye los datos del receptor de la factura.

    El Cliente es el receptor fiscal.
    El correo utilizado es el del Usuario que realizó la operación.
    """

    cliente = transaccion.cliente
    usuario = transaccion.usuario

    if not usuario.email:
        raise ValidationError(
            'El usuario que realizó la operación no posee correo electrónico.'
        )

    receptor = {
        'cPaisRec': 'PRY',
        'dNomRec': cliente.nombre_o_denominacion,
        'dEmailRec': usuario.email,
    }

    if cliente.tipo_persona == Cliente.TipoPersona.FISICA:
        receptor.update({
            # No contribuyente
            'iNatRec': '2',

            # B2C
            'iTiOpe': '2',

            # Cédula paraguaya
            'iTipIDRec': '1',

            'dNumIDRec': cliente.documento,
        })

        return receptor

    if cliente.tipo_persona == Cliente.TipoPersona.JURIDICA:

        if not cliente.digito_verificador:
            raise ValidationError(
                'La persona jurídica no posee dígito verificador.'
            )

        receptor.update({
            # Contribuyente
            'iNatRec': '1',

            # B2B
            'iTiOpe': '1',

            # Persona jurídica
            'iTiContRec': '2',

            'dRucRec': cliente.documento,
            'dDVRec': cliente.digito_verificador,

            # Según estructura resumida de Factura Segura,
            # estos quedan en cero para contribuyentes.
            'iTipIDRec': '0',
            'dNumIDRec': '0',
        })

        return receptor

    raise ValidationError(
        'Tipo de persona no soportado para facturación.'
    )


def validar_configuracion(configuracion):
    """
    Verifica que estén cargados los datos mínimos del emisor.
    """

    campos = {
        'nombre_emisor': 'Razón social',
        'ruc_emisor': 'RUC',
        'dv_emisor': 'DV',
        'timbrado': 'Timbrado',
        'fecha_inicio_timbrado': 'Fecha de inicio de timbrado',
        'establecimiento': 'Establecimiento',
        'punto_expedicion': 'Punto de expedición',
        'direccion': 'Dirección',
        'numero_casa': 'Número de casa',
        'departamento_codigo': 'Código de departamento',
        'departamento_descripcion': 'Departamento',
        'ciudad_codigo': 'Código de ciudad',
        'ciudad_descripcion': 'Ciudad',
    }

    faltantes = []

    for campo, etiqueta in campos.items():
        if not getattr(configuracion, campo, None):
            faltantes.append(etiqueta)

    if not configuracion.actividades_economicas:
        faltantes.append('Actividades económicas')

    if faltantes:
        raise ValidationError(
            'Faltan datos de configuración fiscal: '
            + ', '.join(faltantes)
        )


def construir_json_resumido(*, transaccion, configuracion, numero_documento, fecha_emision=None):
    """
    Construye el JSON_RESUMIDO_DE que será enviado a calcular_de.
    """

    if transaccion.estado != Transaccion.Estado.PAGADA:
        raise ValidationError(
            'Solo se pueden facturar transacciones PAGADAS.'
        )

    validar_configuracion(configuracion)

    monto_factura = obtener_monto_factura(transaccion)

    if monto_factura <= 0:
        raise ValidationError(
            'El monto de la factura debe ser mayor a cero.'
        )

    if fecha_emision is None:
        fecha_emision = timezone.localtime()

    fecha_texto = fecha_emision.strftime(
        '%Y-%m-%dT%H:%M:%S'
    )

    numero_texto = str(numero_documento).zfill(7)

    if len(numero_texto) > 7:
        raise ValidationError(
            'El número de documento no puede superar 7 dígitos.'
        )

    monto_texto = decimal_a_texto(
        monto_factura
    )

    de = {
        # ---------------------------------
        # Documento electrónico
        # ---------------------------------

        'iTipEmi': '1',

        # Factura electrónica
        'iTiDE': '1',

        'dNumTim': str(
            configuracion.timbrado
        ),

        'dFeIniT': (
            configuracion
            .fecha_inicio_timbrado
            .isoformat()
        ),

        'dEst': str(
            configuracion.establecimiento
        ).zfill(3),

        'dPunExp': str(
            configuracion.punto_expedicion
        ).zfill(3),

        'dNumDoc': numero_texto,

        'dFeEmiDE': fecha_texto,

        # ---------------------------------
        # Tipo de operación
        # ---------------------------------

        'iTipTra':
            obtener_tipo_transaccion_sifen(
                transaccion
            ),

        # Ningún impuesto para esta
        # configuración académica inicial.
        'iTImp': '4',

        # Toda factura de Global Exchange
        # se expresa en PYG.
        'cMoneOpe': MONEDA_FACTURA,

        # IMPORTANTE:
        # no enviamos dCondTiCam ni dTiCam
        # porque cMoneOpe = PYG.

        # ---------------------------------
        # Emisor: Global Exchange
        # ---------------------------------

        'dRucEm':
            configuracion.ruc_emisor,

        'dDVEmi':
            configuracion.dv_emisor,

        'iTipCont': str(
            configuracion.tipo_contribuyente
        ),

        'dNomEmi':
            configuracion.nombre_emisor,

        'dDirEmi':
            configuracion.direccion,

        'dNumCas':
            configuracion.numero_casa,

        'cDepEmi':
            configuracion.departamento_codigo,

        'dDesDepEmi':
            configuracion.departamento_descripcion,

        'cCiuEmi':
            configuracion.ciudad_codigo,

        'dDesCiuEmi':
            configuracion.ciudad_descripcion,

        'dTelEmi':
            configuracion.telefono,

        'dEmailE':
            configuracion.email,

        'gActEco': configuracion.actividades_economicas,

        # ---------------------------------
        # Presencia
        # ---------------------------------

        'iIndPres':
            obtener_indicador_presencia(
                transaccion
            ),

        # ---------------------------------
        # Condición: contado
        # ---------------------------------

        'iCondOpe': '1',

        'gPaConEIni': [
            {
                'iTiPago':
                    obtener_tipo_pago(
                        transaccion
                    ),

                'dMonTiPag':
                    monto_texto,

                'cMoneTiPag':
                    'PYG',

                'dTiCamTiPag':
                    '1',
            }
        ],

        # ---------------------------------
        # Ítem
        # ---------------------------------

        'gCamItem': [
            {
                'dCodInt':
                    obtener_codigo_item(
                        transaccion
                    ),

                'dDesProSer':
                    obtener_descripcion_operacion(
                        transaccion
                    ),

                # Factura Segura soporta
                # unidad 77.
                'cUniMed': '77',

                'dCantProSer': '1',

                'dPUniProSer':
                    monto_texto,

                'dDescItem': '0',
                'dDescGloItem': '0',
                'dAntPreUniIt': '0',
                'dAntGloPreUniIt': '0',

                # Afectivacion IVA requerida por Factura Segura
                'iAfecIVA': '3',
                'dPropIVA': '0',
                'dTasaIVA': '0',
            }
        ],

        # ---------------------------------
        # Factura Segura los genera
        # ---------------------------------

        'CDC': '0',
        'dCodSeg': '0',
        'dDVId': '0',
        'dSisFact': '1',

        # ---------------------------------
        # Información adicional KuDE
        # ---------------------------------

        'dInfAdic': (
            f'Global Exchange | '
            f'{obtener_descripcion_operacion(transaccion)} | '
            f'Tasa aplicada: '
            f'{decimal_a_texto(transaccion.tasa_aplicada)} | '
            f'Comisión: '
            f'{decimal_a_texto(transaccion.porcentaje_comision)}% | '
            f'Monto comisión: '
            f'{decimal_a_texto(transaccion.monto_comision)} '
            f'{transaccion.moneda_comision} | '
            f'Operación: {transaccion.id}'
        ),
    }

    # Agregar campos del receptor.
    de.update(
        construir_receptor(
            transaccion
        )
    )

    return de