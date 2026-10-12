"""Lógica de los reportes de auditoría de caja (SCRUM-41).

Los reportes se construyen sobre los arqueos registrados en el cierre de caja
(SCRUM-40). Cada arqueo se clasifica según sus detalles por moneda:

- **Sin discrepancia**: todas las monedas cuadran.
- **Con sobrante**: al menos una moneda tiene sobrante.
- **Con faltante**: al menos una moneda tiene faltante.

Un mismo arqueo puede tener sobrante en una moneda y faltante en otra; en ese
caso aparece en ambos niveles.
"""

from django.db.models import Exists, OuterRef, Prefetch
from django.utils import timezone

from .models import ArqueoCaja, DetalleArqueo

# Encabezados del CSV, en el mismo orden que `filas_csv`
ENCABEZADOS_CSV = [
    'Fecha de cierre', 'Sucursal', 'Caja', 'Cajero', 'Moneda',
    'Saldo registrado', 'Saldo declarado', 'Diferencia', 'Resultado',
]


def arqueos_para_reporte():
    """Devuelve los arqueos anotados con sus discrepancias y con los detalles precargados.

    Agrega a cada arqueo los atributos `tiene_faltante` y `tiene_sobrante`,
    calculados en la base de datos para poder filtrar y contar sin recorrer
    los detalles en Python.

    Returns:
        QuerySet: Arqueos ordenados del más reciente al más antiguo.
    """
    detalles = DetalleArqueo.objects.filter(arqueo=OuterRef('pk'))
    return (
        ArqueoCaja.objects
        .select_related('cajero')
        .prefetch_related(Prefetch('detalles', queryset=DetalleArqueo.objects.order_by('moneda')))
        .annotate(
            tiene_faltante=Exists(detalles.filter(resultado=DetalleArqueo.Resultado.FALTANTE)),
            tiene_sobrante=Exists(detalles.filter(resultado=DetalleArqueo.Resultado.SOBRANTE)),
        )
        .order_by('-fecha_cierre')
    )


def resumen(arqueos):
    """Cuenta los cierres del reporte por nivel de discrepancia.

    Args:
        arqueos: QuerySet devuelto por `arqueos_para_reporte` (ya filtrado).

    Returns:
        dict: Claves `total`, `con_faltante`, `con_sobrante` y `sin_discrepancia`.
    """
    return {
        'total': arqueos.count(),
        'con_faltante': arqueos.filter(tiene_faltante=True).count(),
        'con_sobrante': arqueos.filter(tiene_sobrante=True).count(),
        'sin_discrepancia': arqueos.filter(tiene_faltante=False, tiene_sobrante=False).count(),
    }


def _monto(valor):
    """Formatea un monto para CSV con coma decimal y sin separador de miles (formato de Excel en español)."""
    return f"{valor:.2f}".replace('.', ',')


def filas_csv(arqueos):
    """Genera las filas del CSV: una por cada moneda de cada arqueo.

    Args:
        arqueos: QuerySet devuelto por `arqueos_para_reporte` (ya filtrado).

    Yields:
        list[str]: Valores de la fila en el orden de `ENCABEZADOS_CSV`.
    """
    for arqueo in arqueos:
        cajero = arqueo.cajero.get_full_name() or arqueo.cajero.username
        for detalle in arqueo.detalles.all():
            yield [
                f"{timezone.localtime(arqueo.fecha_cierre):%d/%m/%Y %H:%M}",
                arqueo.sucursal_nombre,
                arqueo.caja_nombre,
                cajero,
                detalle.moneda,
                _monto(detalle.saldo_registrado),
                _monto(detalle.saldo_declarado),
                _monto(detalle.diferencia),
                detalle.get_resultado_display(),
            ]
