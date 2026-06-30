from __future__ import annotations

from datetime import date, datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError
from django.utils import timezone

from incubacion.models import ETLRunAudit
from incubacion.services import (
    PresupuestoETLConfig,
    SqlServerConnectionConfig,
    run_etl_presupuesto,
)


class Command(BaseCommand):
    help = "Run presupuesto incubadoras ETL from Excel to SQL Server destination"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--start-date", required=True, help="Start date in YYYY-MM-DD format")
        parser.add_argument("--end-date", required=True, help="End date in YYYY-MM-DD format")
        parser.add_argument(
            "--excel-path",
            default="",
            help="Path to Excel file (defaults to ETL_PRESUPUESTO.EXCEL_PATH)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Transform only and print counts without deleting/inserting",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Batch size for INSERT operations (default: 1000)",
        )

    def handle(self, *args, **options) -> None:
        start_date = self._parse_date(options["start_date"], "start-date")
        end_date = self._parse_date(options["end_date"], "end-date")

        if end_date < start_date:
            raise CommandError("--end-date must be greater than or equal to --start-date")

        batch_size = options["batch_size"]
        if batch_size <= 0:
            raise CommandError("--batch-size must be greater than zero")

        config, excel_path = self._build_config(options.get("excel_path") or "")
        dry_run = options["dry_run"]

        audit = ETLRunAudit(
            status=ETLRunAudit.STATUS_DRY_RUN if dry_run else ETLRunAudit.STATUS_SUCCESS,
            start_date=start_date,
            end_date=end_date,
            batch_size=batch_size,
            dry_run=dry_run,
            status_message="Ejecutando ETL Presupuesto Incubadoras",
            is_running=True,
            progress_percent=10,
            summary_json={
                "etl_type": "presupuesto_incubadoras",
                "excel_path": excel_path,
            },
        )

        try:
            self._save_audit(audit)

            result = run_etl_presupuesto(
                config=config,
                excel_path=excel_path,
                start_date=start_date,
                end_date=end_date,
                dry_run=dry_run,
                batch_size=batch_size,
            )

            audit.source_rows = int(result.get("source_rows", 0))
            audit.deleted_rows = int(result.get("deleted_rows", 0))
            audit.inserted_rows = int(result.get("inserted_rows", 0))
            audit.status = ETLRunAudit.STATUS_DRY_RUN if dry_run else ETLRunAudit.STATUS_SUCCESS
            audit.status_message = "ETL Presupuesto Incubadoras completada"
            audit.progress_percent = 100
            audit.is_running = False
            audit.ended_at = timezone.now()
            audit.summary_json = {
                "etl_type": "presupuesto_incubadoras",
                "excel_path": excel_path,
                **(result.get("summary") or {}),
            }
            self._save_audit(audit)
        except Exception as exc:
            audit.status = ETLRunAudit.STATUS_FAILED
            audit.error_message = str(exc)
            audit.status_message = "ETL Presupuesto Incubadoras fallida"
            audit.progress_percent = 100
            audit.is_running = False
            audit.ended_at = timezone.now()
            self._save_audit(audit)
            raise CommandError(f"ETL failed: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                "ETL completed. "
                f"source_rows={audit.source_rows}, "
                f"deleted_rows={audit.deleted_rows}, "
                f"inserted_rows={audit.inserted_rows}, "
                f"dry_run={dry_run}"
            )
        )

    @staticmethod
    def _parse_date(value: str, argument_name: str) -> date:
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError as exc:
            raise CommandError(f"--{argument_name} must use YYYY-MM-DD format") from exc

    @staticmethod
    def _save_audit(audit: ETLRunAudit) -> None:
        try:
            audit.save()
        except (OperationalError, ProgrammingError):
            # Audit table may not exist yet if migrations have not been applied.
            pass

    @staticmethod
    def _build_config(excel_path_override: str = "") -> tuple[PresupuestoETLConfig, str]:
        etl_settings = getattr(settings, "ETL_PRESUPUESTO", None)
        if not etl_settings:
            raise CommandError("ETL_PRESUPUESTO settings are missing")

        required_paths = [
            ("DESTINATION", "SERVER"),
            ("DESTINATION", "DATABASE"),
            ("DESTINATION_TABLE",),
            ("DESTINATION_DATE_COLUMN",),
            ("DESTINATION_KEY_COLUMN",),
            ("EXCEL_PATH",),
        ]

        for path in required_paths:
            current = etl_settings
            for key in path:
                if not isinstance(current, dict) or key not in current:
                    dotted = ".".join(path)
                    raise CommandError(f"Missing ETL_PRESUPUESTO setting: {dotted}")
                current = current[key]
            if current in (None, ""):
                dotted = ".".join(path)
                raise CommandError(f"Empty ETL_PRESUPUESTO setting: {dotted}")

        destination_cfg = etl_settings["DESTINATION"]
        destination = SqlServerConnectionConfig(
            server=destination_cfg["SERVER"],
            database=destination_cfg["DATABASE"],
            username=destination_cfg.get("USERNAME", ""),
            password=destination_cfg.get("PASSWORD", ""),
            trusted_connection=bool(destination_cfg.get("TRUSTED_CONNECTION", True)),
            driver=destination_cfg.get("DRIVER", "ODBC Driver 17 for SQL Server"),
            timeout=int(destination_cfg.get("TIMEOUT", 30)),
        )

        excel_path = excel_path_override or str(etl_settings["EXCEL_PATH"])

        config = PresupuestoETLConfig(
            destination=destination,
            destination_table=etl_settings["DESTINATION_TABLE"],
            destination_date_column=etl_settings.get("DESTINATION_DATE_COLUMN", "fecha_fin_mes"),
            destination_key_column=etl_settings.get("DESTINATION_KEY_COLUMN", "centro_costo"),
            sheet_elemento_costo=etl_settings.get("SHEET_ELEMENTO_COSTO", "elemento_costo"),
            sheet_presupuesto=etl_settings.get("SHEET_PRESUPUESTO", "presupuesto"),
        )
        return config, excel_path
