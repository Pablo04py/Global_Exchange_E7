"""Vistas de la aplicación arqueos (cierre de caja, detalle del arqueo, habilitación de cajas y reportes de auditoría)."""

import csv

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from main.views import get_menu_sections, resolve_user_role, resolve_user_roles
from usuarios.decorators import requiere_rol
from . import integracion
from . import reportes
from .forms import CierreCajaForm, FiltroReporteForm
from .models import ArqueoCaja
from .services import cajas_bloqueadas_con_ultimo_cierre, habilitar_caja_bloqueada, registrar_cierre

# Roles que pueden habilitar una caja bloqueada por un cierre.
ROLES_HABILITAR = ('Administrador General',)

# Roles que pueden consultar los reportes de auditoría (SCRUM-41).
# Para habilitar al Supervisor cuando exista en Keycloak, agregarlo aquí.
ROLES_REPORTE = ('Administrador General',)


def _menu(request):
    """Devuelve las secciones del menú lateral según el rol del usuario."""
    return get_menu_sections(
        resolve_user_role(request), None, is_authenticated=True, roles=resolve_user_roles(request)
    )


@requiere_rol('Cajero')
def cerrar_caja(request):
    """Cierre de caja del cajero con arqueo ciego.

    GET muestra un campo por cada moneda del turno abierto del cajero, sin
    revelar el saldo registrado. POST registra el arqueo, bloquea la caja y
    redirige al detalle con la comparación.

    Si el módulo de caja (otras historias) aún no está disponible o el cajero
    no tiene una caja abierta asignada, se muestra un aviso.

    Args:
        request: Petición HTTP de un usuario con rol `Cajero`.

    Returns:
        HttpResponse: Plantilla `arqueos/cerrar_caja.html` o redirección a
        `detalle_arqueo`.
    """
    contexto = {'menu_sections': _menu(request)}
    try:
        turno = integracion.obtener_turno_abierto(request.user)
        monedas = sorted(integracion.obtener_saldo_registrado(turno)) if turno else []
    except integracion.ModuloCajaNoDisponible:
        contexto['modulo_no_disponible'] = True
        return render(request, 'arqueos/cerrar_caja.html', contexto)

    if turno is None:
        return render(request, 'arqueos/cerrar_caja.html', contexto)

    form = CierreCajaForm(request.POST or None, monedas=monedas)
    if request.method == 'POST' and form.is_valid():
        try:
            arqueo = registrar_cierre(request.user, form.saldos_declarados())
        except ValidationError as error:
            form.add_error(None, error.message)
        except integracion.ModuloCajaNoDisponible:
            contexto['modulo_no_disponible'] = True
            return render(request, 'arqueos/cerrar_caja.html', contexto)
        else:
            return redirect('detalle_arqueo', arqueo_id=arqueo.id)

    contexto.update({'caja': integracion.datos_de_caja(turno), 'form': form})
    return render(request, 'arqueos/cerrar_caja.html', contexto)


@requiere_rol('Cajero', 'Administrador General')
def detalle_arqueo(request, arqueo_id):
    """Muestra el resultado de un arqueo: registrado, declarado, diferencia y resultado.

    El cajero solo puede ver sus propios arqueos; el Administrador General
    puede ver cualquiera.

    Args:
        request: Petición HTTP.
        arqueo_id: UUID del arqueo.

    Returns:
        HttpResponse: Plantilla `arqueos/detalle_arqueo.html`.

    Raises:
        Http404: Si el arqueo no existe o pertenece a otro cajero.
    """
    arqueo = get_object_or_404(ArqueoCaja.objects.select_related('cajero'), id=arqueo_id)
    if 'Administrador General' not in request.user.roles and arqueo.cajero != request.user:
        raise Http404
    return render(request, 'arqueos/detalle_arqueo.html', {
        'arqueo': arqueo,
        'detalles': arqueo.detalles.all(),
        'menu_sections': _menu(request),
    })


@requiere_rol(*ROLES_HABILITAR)
def cajas_bloqueadas(request):
    """Lista las cajas bloqueadas por un cierre, con su último arqueo.

    Desde aquí el Administrador General puede habilitarlas nuevamente.

    Args:
        request: Petición HTTP de un Administrador General.

    Returns:
        HttpResponse: Plantilla `arqueos/cajas_bloqueadas.html`.
    """
    contexto = {'menu_sections': _menu(request)}
    try:
        contexto['bloqueadas'] = cajas_bloqueadas_con_ultimo_cierre()
    except integracion.ModuloCajaNoDisponible:
        contexto['modulo_no_disponible'] = True
    return render(request, 'arqueos/cajas_bloqueadas.html', contexto)


@require_POST
@requiere_rol(*ROLES_HABILITAR)
def habilitar_caja(request, caja_id):
    """Habilita una caja bloqueada por un cierre (vuelve a estar disponible).

    Args:
        request: Petición HTTP (POST) de un Administrador General.
        caja_id: Identificador de la caja.

    Returns:
        HttpResponse: Redirección a `cajas_bloqueadas` con un mensaje del resultado.
    """
    try:
        caja = habilitar_caja_bloqueada(caja_id)
    except ValidationError as error:
        messages.error(request, error.messages[0])
    except integracion.ModuloCajaNoDisponible:
        messages.error(request, "El módulo de caja todavía no está disponible.")
    else:
        messages.success(request, f"La caja {caja} fue habilitada y está disponible nuevamente.")
    return redirect('cajas_bloqueadas')


def _reporte_filtrado(request):
    """Arma el formulario de filtros y devuelve los arqueos filtrados del reporte.

    Args:
        request: Petición HTTP (GET con filtros opcionales).

    Returns:
        tuple[FiltroReporteForm, QuerySet]: El formulario y los arqueos filtrados.
    """
    form = FiltroReporteForm(request.GET or None, arqueos=ArqueoCaja.objects.all())
    if form.is_bound:
        form.is_valid()  # completa cleaned_data; los campos con error se ignoran al filtrar
    return form, form.filtrar(reportes.arqueos_para_reporte())


@require_GET
@requiere_rol(*ROLES_REPORTE)
def reporte_arqueos(request):
    """Reporte de auditoría de caja: cierres, saldos e inconsistencias (solo lectura).

    Filtra por fecha, sucursal, cajero y nivel de discrepancia, muestra un
    resumen y ofrece imprimir (impresión del navegador) y exportar a CSV con
    los mismos filtros.

    Args:
        request: Petición HTTP de un Administrador General.

    Returns:
        HttpResponse: Plantilla `arqueos/reporte.html`.
    """
    form, arqueos = _reporte_filtrado(request)
    return render(request, 'arqueos/reporte.html', {
        'form': form,
        'arqueos': arqueos,
        'resumen': reportes.resumen(arqueos),
        'hay_filtros': any(request.GET.values()),
        'generado': timezone.localtime(),
        'menu_sections': _menu(request),
    })


@require_GET
@requiere_rol(*ROLES_REPORTE)
def exportar_reporte_csv(request):
    """Exporta el reporte filtrado a CSV (una fila por moneda de cada arqueo).

    Usa `;` como separador, coma decimal y codificación UTF-8 con BOM para
    que Excel en español lo abra con columnas y acentos correctos.

    Args:
        request: Petición HTTP con los mismos filtros que `reporte_arqueos`.

    Returns:
        HttpResponse: Archivo `reporte_arqueos_<fecha>.csv`.
    """
    _, arqueos = _reporte_filtrado(request)
    nombre = f"reporte_arqueos_{timezone.localtime():%Y%m%d_%H%M}.csv"
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{nombre}"'
    response.write('\ufeff')  # BOM: Excel detecta UTF-8
    escritor = csv.writer(response, delimiter=';')
    escritor.writerow(reportes.ENCABEZADOS_CSV)
    escritor.writerows(reportes.filas_csv(arqueos))
    return response
