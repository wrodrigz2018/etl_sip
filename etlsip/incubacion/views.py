from __future__ import annotations

import os
import tempfile
from datetime import date, datetime

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group, Permission, User
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from incubacion.forms import ETLExecutionForm
from incubacion.management.commands.etl_costo_prod_detalle import Command as ETLCostoProdDetalleCommand
from incubacion.management.commands.etl_incubacion import Command as ETLCommand
from incubacion.management.commands.etl_protein_journal import Command as ETLProteinJournalCommand
from incubacion.management.commands.etl_presupuesto_incubadoras import Command as ETLPresupuestoCommand
from incubacion.management.commands.etl_recepcion import Command as ETLRecepcionCommand
from incubacion.management.commands.etl_cargas import Command as ETLCargasCommand
from incubacion.management.commands.etl_baja_pollito import Command as ETLBajaPollitoCommand
from incubacion.management.commands.etl_venta_pollito import Command as ETLVentaPollitoCommand
from incubacion.management.commands.etl_ovoscopia import Command as ETLOvoscopiaCommand
from incubacion.models import ETLRunAudit


ETL_DEFINITIONS = {
    "incubacion": {
        "label": "ETL Incubacion",
        "command": "etl_incubacion",
        "build_config": ETLCommand._build_config,
        "filter_label": "Codigos Fuente",
    },
    "costo_prod_detalle": {
        "label": "ETL CostoProdDetalle",
        "command": "etl_costo_prod_detalle",
        "build_config": ETLCostoProdDetalleCommand._build_config,
        "filter_label": "Incubadoras",
    },
    "presupuesto_incubadoras": {
        "label": "ETL Presupuesto Incubadoras",
        "command": "etl_presupuesto_incubadoras",
        "build_config": ETLPresupuestoCommand._build_config,
        "filter_label": "Archivo Excel",
    },
    "protein_journal_staging": {
        "label": "Importacion Incubesa - costo por lote",
        "command": "etl_protein_journal",
        "build_config": ETLProteinJournalCommand._build_config,
        "filter_label": "Archivo Excel",
    },
    "recepcion": {
        "label": "ETL Recepcion de Huevos",
        "command": "etl_recepcion",
        "build_config": ETLRecepcionCommand._build_config,
        "filter_label": "Codigo Transaccion",
    },
    "cargas": {
        "label": "Importar cargas de incubación",
        "command": "etl_cargas",
        "build_config": ETLCargasCommand._build_config,
        "filter_label": "Archivo Excel",
    },
    "venta_pollito": {
        "label": "Importar venta de pollito",
        "command": "etl_venta_pollito",
        "build_config": ETLVentaPollitoCommand._build_config,
        "filter_label": "Archivo Excel",
    },
    "baja_pollito": {
        "label": "Importar baja de pollito",
        "command": "etl_baja_pollito",
        "build_config": ETLBajaPollitoCommand._build_config,
        "filter_label": "Archivo Excel",
    },
    "ovoscopia": {
        "label": "Importar ovoscopia",
        "command": "etl_ovoscopia",
        "build_config": ETLOvoscopiaCommand._build_config,
        "filter_label": "Rango de fechas",
    },
}


def index(request):
    """Redirect to ETL dashboard or login."""
    if request.user.is_authenticated:
        return redirect("incubacion:etl_dashboard_incubacion")
    return redirect("incubacion:etl_login")


def etl_login(request):
    """Authenticate users against the local Django database."""
    if request.user.is_authenticated:
        return redirect("incubacion:etl_dashboard_incubacion")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("incubacion:etl_dashboard_incubacion")

        return render(
            request,
            "incubacion/login.html",
            {"error": "Usuario o contraseña incorrectos"},
        )

    return render(request, "incubacion/login.html")


def _ensure_etl_group() -> Group:
    """Ensure etl_executor group exists with proper permissions."""
    group, _ = Group.objects.get_or_create(name="etl_executor")
    # Always sync permissions in case the group already existed without grants.
    permissions = Permission.objects.filter(
        Q(codename__in=["view_etlrunaudit", "change_etlrunaudit"])
        | Q(content_type__app_label="incubacion")
    )
    group.permissions.set(permissions)
    return group


def _get_selected_etl(request) -> str:
    etl_type = (
        request.GET.get("etl")
        or request.GET.get("etl_type")
        or request.POST.get("etl_type")
        or "incubacion"
    )
    return etl_type if etl_type in ETL_DEFINITIONS else "incubacion"


def _get_etl_definition(etl_type: str) -> dict:
    return ETL_DEFINITIONS.get(etl_type, ETL_DEFINITIONS["incubacion"])


@login_required(login_url="incubacion:etl_login")
def etl_logout(request):
    """Logout view."""
    logout(request)
    return redirect("incubacion:etl_login")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
def etl_dashboard(request):
    """Legacy dashboard route. Redirect to dedicated ETL dashboards."""
    selected_etl = _get_selected_etl(request)
    if selected_etl == "costo_prod_detalle":
        return redirect("incubacion:etl_dashboard_costo_prod_detalle")
    if selected_etl == "presupuesto_incubadoras":
        return redirect("incubacion:etl_dashboard_presupuesto")
    if selected_etl == "protein_journal_staging":
        return redirect("incubacion:etl_dashboard_protein_journal")
    if selected_etl == "recepcion":
        return redirect("incubacion:etl_dashboard_recepcion")
    if selected_etl == "cargas":
        return redirect("incubacion:etl_dashboard_cargas")
    if selected_etl == "venta_pollito":
        return redirect("incubacion:etl_dashboard_venta_pollito")
    if selected_etl == "baja_pollito":
        return redirect("incubacion:etl_dashboard_baja_pollito")
    if selected_etl == "ovoscopia":
        return redirect("incubacion:etl_dashboard_ovoscopia")
    return redirect("incubacion:etl_dashboard_incubacion")


def _render_dashboard(request, etl_type: str):
    """Render dashboard for a specific ETL."""
    _ensure_etl_group()

    form = ETLExecutionForm()
    if etl_type == "costo_prod_detalle":
        runs = ETLRunAudit.objects.filter(summary_json__etl_type="costo_prod_detalle")[:20]
    elif etl_type == "presupuesto_incubadoras":
        runs = ETLRunAudit.objects.filter(summary_json__etl_type="presupuesto_incubadoras")[:20]
    elif etl_type == "protein_journal_staging":
        runs = ETLRunAudit.objects.filter(summary_json__etl_type="protein_journal_staging")[:20]
    elif etl_type == "recepcion":
        runs = ETLRunAudit.objects.filter(summary_json__etl_type="recepcion")[:20]
    elif etl_type == "cargas":
        runs = ETLRunAudit.objects.filter(summary_json__etl_type="cargas")[:20]
    elif etl_type == "venta_pollito":
        runs = ETLRunAudit.objects.filter(summary_json__etl_type="venta_pollito")[:20]
    elif etl_type == "baja_pollito":
        runs = ETLRunAudit.objects.filter(summary_json__etl_type="baja_pollito")[:20]
    elif etl_type == "ovoscopia":
        runs = ETLRunAudit.objects.filter(summary_json__etl_type="ovoscopia")[:20]
    else:
        runs = ETLRunAudit.objects.filter(
            Q(summary_json__etl_type="incubacion")
            | Q(summary_json__isnull=True)
        )[:20]
    etl_definition = _get_etl_definition(etl_type)

    execute_url_map = {
        "incubacion": "incubacion:etl_execute_incubacion",
        "costo_prod_detalle": "incubacion:etl_execute_costo_prod_detalle",
        "presupuesto_incubadoras": "incubacion:etl_execute_presupuesto",
        "protein_journal_staging": "incubacion:etl_execute_protein_journal",
        "recepcion": "incubacion:etl_execute_recepcion",
        "cargas": "incubacion:etl_execute_cargas",
        "venta_pollito": "incubacion:etl_execute_venta_pollito",
        "baja_pollito": "incubacion:etl_execute_baja_pollito",
        "ovoscopia": "incubacion:etl_execute_ovoscopia",
    }
    preview_url_map = {
        "incubacion": "incubacion:etl_preview_incubacion",
        "costo_prod_detalle": "incubacion:etl_preview_costo_prod_detalle",
        "presupuesto_incubadoras": "incubacion:etl_preview_presupuesto",
        "protein_journal_staging": "incubacion:etl_preview_protein_journal",
        "recepcion": "incubacion:etl_preview_recepcion",
        "cargas": "incubacion:etl_preview_cargas",
        "venta_pollito": "incubacion:etl_preview_venta_pollito",
        "baja_pollito": "incubacion:etl_preview_baja_pollito",
        "ovoscopia": "incubacion:etl_preview_ovoscopia",
    }

    default_excel_path = ""
    if etl_type == "presupuesto_incubadoras":
        etl_settings = getattr(settings, "ETL_PRESUPUESTO", {})
        default_excel_path = str(etl_settings.get("EXCEL_PATH", ""))
    elif etl_type == "protein_journal_staging":
        etl_settings = getattr(settings, "ETL_PROTEIN_JOURNAL", {})
        default_excel_path = str(etl_settings.get("EXCEL_PATH", ""))
    elif etl_type == "cargas":
        etl_settings = getattr(settings, "ETL_CARGAS", {})
        default_excel_path = str(etl_settings.get("EXCEL_PATH", ""))
    elif etl_type == "venta_pollito":
        etl_settings = getattr(settings, "ETL_VENTA_POLLITO", {})
        default_excel_path = str(etl_settings.get("EXCEL_PATH", ""))
    elif etl_type == "baja_pollito":
        etl_settings = getattr(settings, "ETL_BAJA_POLLITO", {})
        default_excel_path = str(etl_settings.get("EXCEL_PATH", ""))

    context = {
        "form": form,
        "runs": runs,
        "user": request.user,
        "etl_options": ETL_DEFINITIONS,
        "selected_etl": etl_type,
        "etl_label": etl_definition["label"],
        "execute_url": execute_url_map.get(etl_type, "incubacion:etl_execute_incubacion"),
        "preview_url": preview_url_map.get(etl_type, "incubacion:etl_preview_incubacion"),
        "show_excel_controls": etl_type in {"presupuesto_incubadoras", "protein_journal_staging", "cargas", "venta_pollito", "baja_pollito"},
        "is_protein_import": etl_type == "protein_journal_staging",
        "is_cargas_import": etl_type == "cargas",
        "is_venta_pollito_import": etl_type == "venta_pollito",
        "is_baja_pollito_import": etl_type == "baja_pollito",
        "is_ovoscopia_import": etl_type == "ovoscopia",
        "default_excel_path": default_excel_path,
    }
    return render(request, "incubacion/dashboard.html", context)


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
def etl_dashboard_incubacion(request):
    """Dedicated dashboard for ETL Incubacion."""
    return _render_dashboard(request, "incubacion")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
def etl_dashboard_costo_prod_detalle(request):
    """Dedicated dashboard for ETL CostoProdDetalle."""
    return _render_dashboard(request, "costo_prod_detalle")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
def etl_dashboard_presupuesto(request):
    """Dedicated dashboard for ETL Presupuesto Incubadoras."""
    return _render_dashboard(request, "presupuesto_incubadoras")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
def etl_dashboard_protein_journal(request):
    """Dedicated dashboard for ETL ProteinJournal Staging."""
    return _render_dashboard(request, "protein_journal_staging")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
def etl_dashboard_recepcion(request):
    """Dedicated dashboard for ETL Recepcion de Huevos."""
    return _render_dashboard(request, "recepcion")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
def etl_dashboard_cargas(request):
    """Dedicated dashboard for importing incubation loads."""
    return _render_dashboard(request, "cargas")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
def etl_dashboard_venta_pollito(request):
    """Dedicated dashboard for importing chick sales."""
    return _render_dashboard(request, "venta_pollito")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
def etl_dashboard_baja_pollito(request):
    """Dedicated dashboard for importing chick removals."""
    return _render_dashboard(request, "baja_pollito")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
def etl_dashboard_ovoscopia(request):
    return _render_dashboard(request, "ovoscopia")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.change_etlrunaudit", raise_exception=True)
@require_POST
def etl_execute(request):
    """Execute ETL with given parameters."""
    etl_type = _get_selected_etl(request)
    return _execute_etl_for_type(request, etl_type)


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.change_etlrunaudit", raise_exception=True)
@require_POST
def etl_execute_incubacion(request):
    """Execute ETL Incubacion explicitly."""
    return _execute_etl_for_type(request, "incubacion")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.change_etlrunaudit", raise_exception=True)
@require_POST
def etl_execute_costo_prod_detalle(request):
    """Execute ETL CostoProdDetalle explicitly."""
    return _execute_etl_for_type(request, "costo_prod_detalle")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.change_etlrunaudit", raise_exception=True)
@require_POST
def etl_execute_presupuesto(request):
    """Execute ETL Presupuesto Incubadoras explicitly."""
    return _execute_etl_for_type(request, "presupuesto_incubadoras")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.change_etlrunaudit", raise_exception=True)
@require_POST
def etl_execute_protein_journal(request):
    """Execute ETL ProteinJournal Staging explicitly."""
    return _execute_etl_for_type(request, "protein_journal_staging")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.change_etlrunaudit", raise_exception=True)
@require_POST
def etl_execute_recepcion(request):
    """Execute ETL Recepcion de Huevos explicitly."""
    return _execute_etl_for_type(request, "recepcion")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.change_etlrunaudit", raise_exception=True)
@require_POST
def etl_execute_cargas(request):
    """Execute the cargas Excel import explicitly."""
    return _execute_etl_for_type(request, "cargas")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.change_etlrunaudit", raise_exception=True)
@require_POST
def etl_execute_venta_pollito(request):
    """Execute the VentaPollito Excel import explicitly."""
    return _execute_etl_for_type(request, "venta_pollito")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.change_etlrunaudit", raise_exception=True)
@require_POST
def etl_execute_baja_pollito(request):
    """Execute the BajaPollito Excel import explicitly."""
    return _execute_etl_for_type(request, "baja_pollito")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.change_etlrunaudit", raise_exception=True)
@require_POST
def etl_execute_ovoscopia(request):
    return _execute_etl_for_type(request, "ovoscopia")


def _execute_etl_for_type(request, etl_type: str):
    """Execute ETL for a fixed etl_type."""
    form = ETLExecutionForm(request.POST)

    excel_etl_types = {"presupuesto_incubadoras", "protein_journal_staging", "cargas", "venta_pollito", "baja_pollito"}

    if etl_type in excel_etl_types:
        try:
            batch_size = int(request.POST.get("batch_size") or 1000)
        except (TypeError, ValueError):
            return JsonResponse({
                "success": False,
                "errors": {"batch_size": ["Tamaño de lote inválido."]},
            }, status=400)

        if batch_size <= 0:
            return JsonResponse({
                "success": False,
                "errors": {"batch_size": ["El tamaño de lote debe ser mayor a cero."]},
            }, status=400)

        dry_run = str(request.POST.get("dry_run", "")).lower() in {"on", "true", "1", "yes"}
    else:
        if not form.is_valid():
            return JsonResponse({
                "success": False,
                "errors": form.errors,
            }, status=400)

        start_date = form.cleaned_data["start_date"]
        end_date = form.cleaned_data["end_date"]
        batch_size = form.cleaned_data["batch_size"]
        dry_run = form.cleaned_data["dry_run"]

    etl_definition = _get_etl_definition(etl_type)
    temp_file_path: str | None = None

    excel_path_override = ""
    start_date: date
    end_date: date
    if etl_type in excel_etl_types:
        uploaded_excel = request.FILES.get("excel_file")
        if uploaded_excel is None:
            return JsonResponse({
                "success": False,
                "errors": {"excel_file": ["Debe seleccionar un archivo Excel."]},
            }, status=400)

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
            for chunk in uploaded_excel.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        excel_path_override = temp_file_path

    try:
        # Build ETL config and run
        resolved_excel_path: str | None = None
        if etl_type in excel_etl_types:
            config, resolved_excel_path = etl_definition["build_config"](excel_path_override)
            if etl_type == "presupuesto_incubadoras":
                from incubacion.services import get_presupuesto_date_range

                start_date, end_date = get_presupuesto_date_range(
                    excel_path=resolved_excel_path,
                    sheet_elemento_costo=config.sheet_elemento_costo,
                    sheet_presupuesto=config.sheet_presupuesto,
                )
            else:
                from incubacion.services import get_cargas_date_range, get_protein_journal_date_range

                if etl_type == "cargas":
                    start_date, end_date = get_cargas_date_range(
                        excel_path=resolved_excel_path,
                        sheet_data=config.sheet_data,
                    )
                elif etl_type == "venta_pollito":
                    from incubacion.services import get_venta_pollito_date_range

                    start_date, end_date = get_venta_pollito_date_range(
                        excel_path=resolved_excel_path,
                        sheet_data=config.sheet_data,
                    )
                elif etl_type == "baja_pollito":
                    from incubacion.services import get_baja_pollito_date_range

                    start_date, end_date = get_baja_pollito_date_range(
                        excel_path=resolved_excel_path,
                        sheet_data=config.sheet_data,
                    )
                else:
                    start_date, end_date = get_protein_journal_date_range(
                        excel_path=resolved_excel_path,
                        sheet_data=config.sheet_data,
                        sheet_mapping=config.sheet_mapping,
                    )
        else:
            config = etl_definition["build_config"]()

        # Create audit record once the date range is known.
        audit = ETLRunAudit(
            status=ETLRunAudit.STATUS_RUNNING,
            start_date=start_date,
            end_date=end_date,
            batch_size=batch_size,
            dry_run=dry_run,
            is_running=True,
            status_message="Iniciando...",
            summary_json={"etl_type": etl_type},
        )
        audit.save()

        audit.status_message = "Extrayendo datos..."
        audit.progress_percent = 25
        audit.save(update_fields=["status_message", "progress_percent"])

        result = _run_etl_with_progress(
            etl_type=etl_type,
            config=config,
            excel_path=resolved_excel_path,
            start_date=start_date,
            end_date=end_date,
            dry_run=dry_run,
            batch_size=batch_size,
            audit=audit,
        )

        audit.status_message = "Completado"
        audit.progress_percent = 100
        audit.source_rows = result["source_rows"]
        audit.deleted_rows = result["deleted_rows"]
        audit.inserted_rows = result["inserted_rows"]
        summary_payload = {"etl_type": etl_type}
        if "summary" in result:
            summary_payload["summary"] = result["summary"]
        audit.summary_json = summary_payload
        audit.status = (
            ETLRunAudit.STATUS_DRY_RUN if dry_run else ETLRunAudit.STATUS_SUCCESS
        )
        audit.ended_at = datetime.now()
        audit.is_running = False
        audit.save()

        return JsonResponse({
            "success": True,
            "run_id": audit.id,
            "message": f"{etl_definition['label']} completado: {result['source_rows']} filas procesadas",
        })

    except Exception as exc:
        if "audit" in locals():
            audit.status = ETLRunAudit.STATUS_FAILED
            audit.error_message = str(exc)
            audit.status_message = f"Error: {str(exc)[:100]}"
            audit.is_running = False
            audit.ended_at = datetime.now()
            audit.save()

        return JsonResponse({
            "success": False,
            "run_id": audit.id if "audit" in locals() else None,
            "message": f"{etl_definition['label']} fallo: {str(exc)}",
        }, status=500)
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def _run_etl_with_progress(etl_type, config, excel_path, start_date, end_date, dry_run, batch_size, audit):
    """Run ETL and update audit progress."""
    from incubacion.services import (
        delete_destination_range,
        extract_rows,
        extract_rows_costo_prod_detalle,
        extract_rows_recepcion,
        extract_rows_ovoscopia,
        insert_rows,
        insert_rows_recepcion,
        month_end,
        open_connection,
        run_etl_protein_journal,
        run_etl_presupuesto,
    )

    if etl_type == "presupuesto_incubadoras":
        if not excel_path:
            raise ValueError("No Excel path provided for presupuesto ETL")

        audit.status_message = "Leyendo archivo Excel..."
        audit.progress_percent = 40
        audit.save(update_fields=["status_message", "progress_percent"])

        result = run_etl_presupuesto(
            config=config,
            excel_path=excel_path,
            start_date=start_date,
            end_date=end_date,
            dry_run=dry_run,
            batch_size=batch_size,
        )

        return {
            "source_rows": int(result.get("source_rows", 0)),
            "deleted_rows": int(result.get("deleted_rows", 0)),
            "inserted_rows": int(result.get("inserted_rows", 0)),
            "summary": result.get("summary", {}),
        }

    if etl_type == "protein_journal_staging":
        if not excel_path:
            raise ValueError("No Excel path provided for ProteinJournal ETL")

        audit.status_message = "Leyendo archivo Excel..."
        audit.progress_percent = 40
        audit.save(update_fields=["status_message", "progress_percent"])

        result = run_etl_protein_journal(
            config=config,
            excel_path=excel_path,
            start_date=start_date,
            end_date=end_date,
            dry_run=dry_run,
            batch_size=batch_size,
        )

        return {
            "source_rows": int(result.get("source_rows", 0)),
            "deleted_rows": int(result.get("deleted_rows", 0)),
            "inserted_rows": int(result.get("inserted_rows", 0)),
            "summary": result.get("summary", {}),
        }

    if etl_type == "cargas":
        if not excel_path:
            raise ValueError("No Excel path provided for cargas ETL")
        from incubacion.services import run_etl_cargas

        audit.status_message = "Leyendo archivo Excel..."
        audit.progress_percent = 40
        audit.save(update_fields=["status_message", "progress_percent"])
        result = run_etl_cargas(
            config=config,
            excel_path=excel_path,
            dry_run=dry_run,
            batch_size=batch_size,
        )
        return {
            "source_rows": int(result.get("source_rows", 0)),
            "deleted_rows": int(result.get("deleted_rows", 0)),
            "inserted_rows": int(result.get("inserted_rows", 0)),
            "summary": result.get("summary", {}),
        }

    if etl_type == "venta_pollito":
        if not excel_path:
            raise ValueError("No Excel path provided for VentaPollito ETL")
        from incubacion.services import run_etl_venta_pollito

        audit.status_message = "Leyendo archivo Excel..."
        audit.progress_percent = 40
        audit.save(update_fields=["status_message", "progress_percent"])
        result = run_etl_venta_pollito(
            config=config,
            excel_path=excel_path,
            dry_run=dry_run,
            batch_size=batch_size,
        )
        return {
            "source_rows": int(result.get("source_rows", 0)),
            "deleted_rows": int(result.get("deleted_rows", 0)),
            "inserted_rows": int(result.get("inserted_rows", 0)),
            "summary": result.get("summary", {}),
        }

    if etl_type == "baja_pollito":
        if not excel_path:
            raise ValueError("No Excel path provided for BajaPollito ETL")
        from incubacion.services import run_etl_baja_pollito

        audit.status_message = "Leyendo archivo Excel..."
        audit.progress_percent = 40
        audit.save(update_fields=["status_message", "progress_percent"])
        result = run_etl_baja_pollito(
            config=config,
            excel_path=excel_path,
            dry_run=dry_run,
            batch_size=batch_size,
        )
        return {
            "source_rows": int(result.get("source_rows", 0)),
            "deleted_rows": int(result.get("deleted_rows", 0)),
            "inserted_rows": int(result.get("inserted_rows", 0)),
            "summary": result.get("summary", {}),
        }

    if etl_type == "ovoscopia":
        from incubacion.services import run_etl_ovoscopia
        result = run_etl_ovoscopia(config, start_date, end_date, dry_run, batch_size)
        return {
            "source_rows": int(result["source_rows"]),
            "deleted_rows": int(result["deleted_rows"]),
            "inserted_rows": int(result["inserted_rows"]),
            "summary": {"etl_type": etl_type},
        }

    source_conn = open_connection(config.source)
    destination_conn = open_connection(config.destination)

    try:
        audit.status_message = "Extrayendo datos..."
        audit.progress_percent = 25
        audit.save(update_fields=["status_message", "progress_percent"])

        if etl_type == "costo_prod_detalle":
            columns, rows = extract_rows_costo_prod_detalle(
                source_conn=source_conn,
                source_table=config.source_table,
                start_date=start_date,
                end_date=end_date,
                hatcheries=config.hatcheries,
                species_type=config.species_type,
                farm_type=config.farm_type,
            )
            delete_start_date = month_end(start_date)
            delete_end_date = month_end(end_date)
        elif etl_type == "recepcion":
            columns, rows = extract_rows_recepcion(
                source_conn=source_conn,
                source_table=config.source_table,
                start_date=start_date,
                end_date=end_date,
                egg_trans_code=config.egg_trans_code,
                facility_type=config.facility_type,
            )
            delete_start_date = start_date
            delete_end_date = end_date
        else:
            columns, rows = extract_rows(
                source_conn=source_conn,
                source_table=config.source_table,
                start_date=start_date,
                end_date=end_date,
                source_codes=config.source_codes,
            )
            delete_start_date = start_date
            delete_end_date = end_date

        if dry_run:
            return {
                "source_rows": len(rows),
                "deleted_rows": 0,
                "inserted_rows": 0,
            }

        audit.status_message = "Borrando datos previos..."
        audit.progress_percent = 50
        audit.save(update_fields=["status_message", "progress_percent"])

        destination_conn.autocommit = False
        deleted_rows = delete_destination_range(
            destination_conn=destination_conn,
            destination_table=config.destination_table,
            destination_date_column=config.destination_date_column,
            start_date=delete_start_date,
            end_date=delete_end_date,
        )

        audit.status_message = "Insertando datos..."
        audit.progress_percent = 75
        audit.save(update_fields=["status_message", "progress_percent"])

        inserted_rows = (insert_rows_recepcion if etl_type == "recepcion" else insert_rows)(
            destination_conn=destination_conn,
            destination_table=config.destination_table,
            columns=columns,
            rows=rows,
            batch_size=batch_size,
        )
        destination_conn.commit()

        # Calculate summary statistics
        audit.status_message = "Calculando estadísticas..."
        audit.progress_percent = 90
        audit.save(update_fields=["status_message", "progress_percent"])

        from incubacion.services import calculate_data_summary
        summary = calculate_data_summary(
            destination_conn=destination_conn,
            destination_table=config.destination_table,
            destination_date_column=config.destination_date_column,
            start_date=delete_start_date,
            end_date=delete_end_date,
            batch_size=batch_size,
        )

        return {
            "source_rows": len(rows),
            "deleted_rows": deleted_rows,
            "inserted_rows": inserted_rows,
            "summary": summary,
        }
    except Exception:
        destination_conn.rollback()
        raise
    finally:
        source_conn.close()
        destination_conn.close()


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
@require_GET
def etl_preview(request):
    """Return data preview as JSON."""
    etl_type = _get_selected_etl(request)
    return _etl_preview_for_type(request, etl_type)


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
@require_GET
def etl_preview_incubacion(request):
    """Return ETL Incubacion preview as JSON."""
    return _etl_preview_for_type(request, "incubacion")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
@require_GET
def etl_preview_costo_prod_detalle(request):
    """Return ETL CostoProdDetalle preview as JSON."""
    return _etl_preview_for_type(request, "costo_prod_detalle")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
@require_POST
def etl_preview_presupuesto(request):
    """Return ETL Presupuesto Incubadoras preview as JSON."""
    return _etl_preview_for_type(request, "presupuesto_incubadoras")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
@require_POST
def etl_preview_protein_journal(request):
    """Return ETL ProteinJournal Staging preview as JSON."""
    return _etl_preview_for_type(request, "protein_journal_staging")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
@require_GET
def etl_preview_recepcion(request):
    """Return ETL Recepcion de Huevos preview as JSON."""
    return _etl_preview_for_type(request, "recepcion")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
@require_POST
def etl_preview_cargas(request):
    """Return cargas Excel preview as JSON."""
    return _etl_preview_for_type(request, "cargas")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
@require_POST
def etl_preview_venta_pollito(request):
    """Return VentaPollito Excel preview as JSON."""
    return _etl_preview_for_type(request, "venta_pollito")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
@require_POST
def etl_preview_baja_pollito(request):
    """Return BajaPollito Excel preview as JSON."""
    return _etl_preview_for_type(request, "baja_pollito")


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
@require_GET
def etl_preview_ovoscopia(request):
    return _etl_preview_for_type(request, "ovoscopia")


def _etl_preview_for_type(request, etl_type: str):
    """Return data preview JSON for a fixed etl_type."""
    from incubacion.services import (
        extract_rows,
        extract_rows_costo_prod_detalle,
        extract_rows_recepcion,
        extract_rows_ovoscopia,
        get_destination_columns,
        get_protein_journal_date_range,
        get_presupuesto_date_range,
        map_columns_and_rows,
        open_connection,
        read_protein_journal_excel,
        read_presupuesto_excel,
        transform_protein_journal_rows,
        transform_presupuesto_rows,
        read_cargas_excel,
        transform_cargas_rows,
        read_venta_pollito_excel,
        transform_venta_pollito_rows,
        read_baja_pollito_excel,
        transform_baja_pollito_rows,
        get_cargas_date_range,
    )

    excel_etl_types = {"presupuesto_incubadoras", "protein_journal_staging", "cargas"}

    if etl_type in excel_etl_types:
        start_date = date.today()
        end_date = date.today()
    else:
        # Parse form parameters
        form = ETLExecutionForm(request.GET)
        if not form.is_valid():
            return JsonResponse({
                "success": False,
                "errors": form.errors,
            }, status=400)

        start_date = form.cleaned_data["start_date"]
        end_date = form.cleaned_data["end_date"]

    etl_definition = _get_etl_definition(etl_type)
    limit_source = request.POST if etl_type in excel_etl_types else request.GET
    limit = int(limit_source.get("limit", 5))

    try:
        # Build ETL config
        if etl_type in excel_etl_types:
            uploaded_excel = request.FILES.get("excel_file")
            temp_preview_path: str | None = None
            if uploaded_excel is None:
                return JsonResponse({
                    "success": False,
                    "error": "Debe seleccionar un archivo Excel para vista previa.",
                }, status=400)

            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
                for chunk in uploaded_excel.chunks():
                    temp_file.write(chunk)
                temp_preview_path = temp_file.name

            excel_path_override = temp_preview_path
            config, resolved_excel_path = etl_definition["build_config"](excel_path_override)
            try:
                if etl_type == "presupuesto_incubadoras":
                    start_date, end_date = get_presupuesto_date_range(
                        excel_path=resolved_excel_path,
                        sheet_elemento_costo=config.sheet_elemento_costo,
                        sheet_presupuesto=config.sheet_presupuesto,
                    )

                    elemento_map, headers, presupuesto_rows = read_presupuesto_excel(
                        excel_path=resolved_excel_path,
                        sheet_elemento_costo=config.sheet_elemento_costo,
                        sheet_presupuesto=config.sheet_presupuesto,
                    )
                    mapped_columns, mapped_rows, _keys, metrics = transform_presupuesto_rows(
                        elemento_map=elemento_map,
                        presupuesto_headers=headers,
                        presupuesto_rows=presupuesto_rows,
                        start_date=start_date,
                        end_date=end_date,
                        load_timestamp=datetime.now(),
                    )
                else:
                    if etl_type == "cargas":
                        start_date, end_date = get_cargas_date_range(
                            excel_path=resolved_excel_path,
                            sheet_data=config.sheet_data,
                        )
                        mapped_columns, mapped_rows, _keys, metrics = transform_cargas_rows(
                            *read_cargas_excel(resolved_excel_path, config.sheet_data),
                        )
                    elif etl_type == "venta_pollito":
                        from incubacion.services import get_venta_pollito_date_range

                        start_date, end_date = get_venta_pollito_date_range(
                            excel_path=resolved_excel_path,
                            sheet_data=config.sheet_data,
                        )
                        mapped_columns, mapped_rows, _keys, metrics = transform_venta_pollito_rows(
                            *read_venta_pollito_excel(resolved_excel_path, config.sheet_data),
                        )
                    elif etl_type == "baja_pollito":
                        from incubacion.services import get_baja_pollito_date_range

                        start_date, end_date = get_baja_pollito_date_range(
                            excel_path=resolved_excel_path,
                            sheet_data=config.sheet_data,
                        )
                        mapped_columns, mapped_rows, _keys, metrics = transform_baja_pollito_rows(
                            *read_baja_pollito_excel(resolved_excel_path, config.sheet_data),
                        )
                    else:
                        start_date, end_date = get_protein_journal_date_range(
                            excel_path=resolved_excel_path,
                            sheet_data=config.sheet_data,
                            sheet_mapping=config.sheet_mapping,
                        )

                        elemento_map, headers, data_rows = read_protein_journal_excel(
                            excel_path=resolved_excel_path,
                            sheet_data=config.sheet_data,
                            sheet_mapping=config.sheet_mapping,
                        )
                        mapped_columns, mapped_rows, _keys, metrics = transform_protein_journal_rows(
                            elemento_map=elemento_map,
                            data_headers=headers,
                            data_rows=data_rows,
                            start_date=start_date,
                            end_date=end_date,
                            load_timestamp=datetime.now(),
                        )

                sample_rows = mapped_rows[:limit]
                sample_data = [list(row) for row in sample_rows]
                return JsonResponse({
                    "success": True,
                    "etl_type": etl_type,
                    "etl_label": etl_definition["label"],
                    "preview_source": "excel_file",
                    "source_file_name": uploaded_excel.name,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "filter_label": etl_definition["filter_label"],
                    "filter_values": [uploaded_excel.name],
                    "total_rows": metrics.get("transformed_rows", len(mapped_rows)),
                    "columns": mapped_columns,
                    "sample_data": sample_data,
                    "sample_limit": limit,
                })
            finally:
                if temp_preview_path and os.path.exists(temp_preview_path):
                    os.remove(temp_preview_path)

        config = etl_definition["build_config"]()
        
        # Extract data
        source_conn = open_connection(config.source)
        try:
            if etl_type == "costo_prod_detalle":
                columns, rows = extract_rows_costo_prod_detalle(
                    source_conn=source_conn,
                    source_table=config.source_table,
                    start_date=start_date,
                    end_date=end_date,
                    hatcheries=config.hatcheries,
                    species_type=config.species_type,
                    farm_type=config.farm_type,
                )
            elif etl_type == "ovoscopia":
                columns, rows = extract_rows_ovoscopia(source_conn, start_date, end_date)
            elif etl_type == "recepcion":
                columns, rows = extract_rows_recepcion(
                    source_conn=source_conn,
                    source_table=config.source_table,
                    start_date=start_date,
                    end_date=end_date,
                    egg_trans_code=config.egg_trans_code,
                    facility_type=config.facility_type,
                )
            else:
                columns, rows = extract_rows(
                    source_conn=source_conn,
                    source_table=config.source_table,
                    start_date=start_date,
                    end_date=end_date,
                    source_codes=config.source_codes,
                )
        finally:
            source_conn.close()

        # Get destination columns and map
        dest_conn = open_connection(config.destination)
        try:
            dest_columns = get_destination_columns(
                destination_conn=dest_conn,
                destination_table=config.destination_table,
            )
        finally:
            dest_conn.close()

        mapped_columns, mapped_rows = map_columns_and_rows(
            source_columns=columns,
            source_rows=rows,
            destination_columns=dest_columns,
        )

        # Prepare response
        if etl_type == "costo_prod_detalle":
            filter_values = list(config.hatcheries)
        elif etl_type == "venta_pollito":
            filter_values = [f"Hoja={config.sheet_data}"]
        elif etl_type == "baja_pollito":
            filter_values = [f"Hoja={config.sheet_data}", "tipo=Eliminados"]
        elif etl_type == "ovoscopia":
            filter_values = [f"HatchDate={start_date.isoformat()}..{end_date.isoformat()}"]
        elif etl_type == "recepcion":
            filter_values = [f"EggTransCode={config.egg_trans_code}", f"FacilityType={config.facility_type}"]
        else:
            filter_values = list(config.source_codes)
        sample_rows = mapped_rows[:limit]
        
        # Convert rows to list format
        sample_data = [list(row) for row in sample_rows]

        return JsonResponse({
            "success": True,
            "etl_type": etl_type,
            "etl_label": etl_definition["label"],
            "preview_source": "database",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "filter_label": etl_definition["filter_label"],
            "filter_values": filter_values,
            "total_rows": len(rows),
            "columns": mapped_columns,
            "sample_data": sample_data,
            "sample_limit": limit,
        })

    except Exception as exc:
        return JsonResponse({
            "success": False,
            "error": str(exc),
        }, status=500)


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
@require_GET
def etl_status(request):
    """Return current ETL run status as JSON for polling."""
    run_id = request.GET.get("run_id")

    if not run_id:
        # Return last run
        last_run = ETLRunAudit.objects.last()
        if not last_run:
            return JsonResponse({"status": "no_runs"})

        return JsonResponse({
            "run_id": last_run.id,
            "status": last_run.status,
            "status_message": last_run.status_message,
            "progress_percent": last_run.progress_percent,
            "is_running": last_run.is_running,
            "source_rows": last_run.source_rows,
            "deleted_rows": last_run.deleted_rows,
            "inserted_rows": last_run.inserted_rows,
            "error_message": last_run.error_message,
        })

    try:
        run = ETLRunAudit.objects.get(id=int(run_id))
        return JsonResponse({
            "run_id": run.id,
            "status": run.status,
            "status_message": run.status_message,
            "progress_percent": run.progress_percent,
            "is_running": run.is_running,
            "source_rows": run.source_rows,
            "deleted_rows": run.deleted_rows,
            "inserted_rows": run.inserted_rows,
            "error_message": run.error_message,
            "summary": run.get_summary().get("summary", {}),
            "etl_type": run.get_summary().get("etl_type", "incubacion"),
        })
    except (ETLRunAudit.DoesNotExist, ValueError):
        return JsonResponse({"status": "not_found"}, status=404)


@login_required(login_url="incubacion:etl_login")
@permission_required("incubacion.view_etlrunaudit", raise_exception=True)
@require_GET
def etl_history(request):
    """Return paginated history as JSON."""
    page = int(request.GET.get("page", 1))
    per_page = int(request.GET.get("per_page", 20))

    runs = ETLRunAudit.objects.all()
    total = runs.count()
    start = (page - 1) * per_page
    end = start + per_page
    page_runs = runs[start:end]

    return JsonResponse({
        "total": total,
        "page": page,
        "per_page": per_page,
        "runs": [
            {
                "id": run.id,
                "status": run.status,
                "started_at": run.started_at.isoformat(),
                "ended_at": run.ended_at.isoformat() if run.ended_at else None,
                "start_date": run.start_date.isoformat(),
                "end_date": run.end_date.isoformat(),
                "source_rows": run.source_rows,
                "deleted_rows": run.deleted_rows,
                "inserted_rows": run.inserted_rows,
                "error_message": run.error_message,
                "dry_run": run.dry_run,
            }
            for run in page_runs
        ],
    })
