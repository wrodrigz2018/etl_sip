from __future__ import annotations

import json
from datetime import date, datetime

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group, Permission, User
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from incubacion.auth import KeycloakAuthenticator
from incubacion.forms import ETLExecutionForm
from incubacion.management.commands.etl_costo_prod_detalle import Command as ETLCostoProdDetalleCommand
from incubacion.management.commands.etl_incubacion import Command as ETLCommand
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
}


def index(request):
    """Redirect to ETL dashboard or login."""
    if request.user.is_authenticated:
        return redirect("incubacion:etl_dashboard_incubacion")
    return redirect("incubacion:etl_login")


def _get_keycloak_authenticator() -> KeycloakAuthenticator | None:
    """Get Keycloak authenticator if enabled."""
    if not getattr(settings, 'USE_KEYCLOAK', False):
        return None

    config = getattr(settings, 'KEYCLOAK_CONFIG', {})
    return KeycloakAuthenticator(
        server_url=config.get('SERVER_URL', ''),
        client_id=config.get('CLIENT_ID', ''),
        realm_name=config.get('REALM_NAME', ''),
    )


def etl_login(request):
    """Login view supporting both Keycloak and local authentication."""
    if request.user.is_authenticated:
        return redirect("incubacion:etl_dashboard_incubacion")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        keycloak_auth = _get_keycloak_authenticator()

        # Try Keycloak first if enabled
        user_info = None
        if keycloak_auth:
            user_info = keycloak_auth.authenticate(username, password)

        if user_info:
            # Create or update user from Keycloak
            user_obj, created = User.objects.get_or_create(
                username=user_info['username'],
                defaults={
                    "email": user_info['email'],
                    "first_name": user_info['first_name'],
                    "last_name": user_info['last_name'],
                }
            )

            if not created:
                user_obj.email = user_info['email']
                user_obj.first_name = user_info['first_name']
                user_obj.last_name = user_info['last_name']
                user_obj.save()

            # Update password
            user_obj.set_password(password)
            user_obj.save()

            # Add to etl_executor group
            etl_group, _ = Group.objects.get_or_create(name="etl_executor")
            user_obj.groups.add(etl_group)

            # Authenticate and login
            user = authenticate(request, username=user_info['username'], password=password)
            if user is not None:
                login(request, user)
                return redirect("incubacion:etl_dashboard_incubacion")

        elif not keycloak_auth:
            # Fallback to local authentication if Keycloak not enabled
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect("incubacion:etl_dashboard_incubacion")

        # Error message
        error_msg = (
            "Usuario o contraseña incorrectos en Keycloak"
            if keycloak_auth
            else "Usuario o contraseña incorrectos"
        )
        context = {"error": error_msg}
        return render(request, "incubacion/login.html", context)

    return render(request, "incubacion/login.html")


def _ensure_etl_group() -> Group:
    """Ensure etl_executor group exists with proper permissions."""
    group, created = Group.objects.get_or_create(name="etl_executor")
    if created:
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
    return redirect("incubacion:etl_dashboard_incubacion")


def _render_dashboard(request, etl_type: str):
    """Render dashboard for a specific ETL."""
    _ensure_etl_group()

    form = ETLExecutionForm()
    if etl_type == "costo_prod_detalle":
        runs = ETLRunAudit.objects.filter(summary_json__etl_type="costo_prod_detalle")[:20]
    else:
        runs = ETLRunAudit.objects.filter(
            Q(summary_json__etl_type="incubacion")
            | Q(summary_json__isnull=True)
        )[:20]
    etl_definition = _get_etl_definition(etl_type)

    context = {
        "form": form,
        "runs": runs,
        "user": request.user,
        "etl_options": ETL_DEFINITIONS,
        "selected_etl": etl_type,
        "etl_label": etl_definition["label"],
        "execute_url": (
            "incubacion:etl_execute_costo_prod_detalle"
            if etl_type == "costo_prod_detalle"
            else "incubacion:etl_execute_incubacion"
        ),
        "preview_url": (
            "incubacion:etl_preview_costo_prod_detalle"
            if etl_type == "costo_prod_detalle"
            else "incubacion:etl_preview_incubacion"
        ),
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


def _execute_etl_for_type(request, etl_type: str):
    """Execute ETL for a fixed etl_type."""
    form = ETLExecutionForm(request.POST)

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

    # Create audit record
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

    try:
        # Build ETL config and run
        config = etl_definition["build_config"]()
        audit.status_message = "Extrayendo datos..."
        audit.progress_percent = 25
        audit.save(update_fields=["status_message", "progress_percent"])

        result = _run_etl_with_progress(
            etl_type=etl_type,
            config=config,
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
        audit.status = ETLRunAudit.STATUS_FAILED
        audit.error_message = str(exc)
        audit.status_message = f"Error: {str(exc)[:100]}"
        audit.is_running = False
        audit.ended_at = datetime.now()
        audit.save()

        return JsonResponse({
            "success": False,
            "run_id": audit.id,
            "message": f"{etl_definition['label']} fallo: {str(exc)}",
        }, status=500)


def _run_etl_with_progress(etl_type, config, start_date, end_date, dry_run, batch_size, audit):
    """Run ETL and update audit progress."""
    from incubacion.services import (
        delete_destination_range,
        extract_rows,
        extract_rows_costo_prod_detalle,
        insert_rows,
        month_end,
        open_connection,
    )

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

        inserted_rows = insert_rows(
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


def _etl_preview_for_type(request, etl_type: str):
    """Return data preview JSON for a fixed etl_type."""
    from incubacion.services import (
        extract_rows,
        extract_rows_costo_prod_detalle,
        get_destination_columns,
        map_columns_and_rows,
        open_connection,
    )

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
    limit = int(request.GET.get("limit", 5))

    try:
        # Build ETL config
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
        filter_values = list(config.hatcheries) if etl_type == "costo_prod_detalle" else list(config.source_codes)
        sample_rows = mapped_rows[:limit]
        
        # Convert rows to list format
        sample_data = [list(row) for row in sample_rows]

        return JsonResponse({
            "success": True,
            "etl_type": etl_type,
            "etl_label": etl_definition["label"],
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
