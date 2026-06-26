from __future__ import annotations

from datetime import date, datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError
from django.utils import timezone

from incubacion.models import ETLRunAudit
from incubacion.services import (
    CostoProdDetalleETLConfig,
    SqlServerConnectionConfig,
    run_etl_costo_prod_detalle,
)


class Command(BaseCommand):
    help = "Run CostoProdDetalle ETL from SQL Server source to SQL Server destination"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--start-date", required=True, help="Start date in YYYY-MM-DD format")
        parser.add_argument("--end-date", required=True, help="End date in YYYY-MM-DD format")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Extract only and print counts without deleting/inserting",
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

        config = self._build_config()
        dry_run = options["dry_run"]

        audit = ETLRunAudit(
            status=ETLRunAudit.STATUS_DRY_RUN if dry_run else ETLRunAudit.STATUS_SUCCESS,
            start_date=start_date,
            end_date=end_date,
            batch_size=batch_size,
            dry_run=dry_run,
            status_message="Ejecutando ETL CostoProdDetalle",
            is_running=True,
            progress_percent=10,
        )

        try:
            self._save_audit(audit)

            result = run_etl_costo_prod_detalle(
                config=config,
                start_date=start_date,
                end_date=end_date,
                dry_run=dry_run,
                batch_size=batch_size,
            )

            audit.source_rows = result["source_rows"]
            audit.deleted_rows = result["deleted_rows"]
            audit.inserted_rows = result["inserted_rows"]
            audit.status = ETLRunAudit.STATUS_DRY_RUN if dry_run else ETLRunAudit.STATUS_SUCCESS
            audit.status_message = "ETL CostoProdDetalle completada"
            audit.progress_percent = 100
            audit.is_running = False
            audit.ended_at = timezone.now()
            self._save_audit(audit)
        except Exception as exc:
            audit.status = ETLRunAudit.STATUS_FAILED
            audit.error_message = str(exc)
            audit.status_message = "ETL CostoProdDetalle fallida"
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
    def _build_config() -> CostoProdDetalleETLConfig:
        etl_settings = getattr(settings, "ETL_COSTO_PROD_DETALLE", None)
        if not etl_settings:
            raise CommandError("ETL_COSTO_PROD_DETALLE settings are missing")

        required_paths = [
            ("SOURCE", "SERVER"),
            ("SOURCE", "DATABASE"),
            ("DESTINATION", "SERVER"),
            ("DESTINATION", "DATABASE"),
            ("SOURCE_TABLE",),
            ("DESTINATION_TABLE",),
            ("DESTINATION_DATE_COLUMN",),
        ]

        for path in required_paths:
            current = etl_settings
            for key in path:
                if not isinstance(current, dict) or key not in current:
                    dotted = ".".join(path)
                    raise CommandError(f"Missing ETL_COSTO_PROD_DETALLE setting: {dotted}")
                current = current[key]
            if current in (None, ""):
                dotted = ".".join(path)
                raise CommandError(f"Empty ETL_COSTO_PROD_DETALLE setting: {dotted}")

        source_cfg = etl_settings["SOURCE"]
        destination_cfg = etl_settings["DESTINATION"]
        hatcheries = tuple(etl_settings.get("HATCHERIES") or ())

        if not hatcheries:
            raise CommandError("ETL_COSTO_PROD_DETALLE.HATCHERIES must contain at least one value")

        source = SqlServerConnectionConfig(
            server=source_cfg["SERVER"],
            database=source_cfg["DATABASE"],
            username=source_cfg.get("USERNAME", ""),
            password=source_cfg.get("PASSWORD", ""),
            trusted_connection=bool(source_cfg.get("TRUSTED_CONNECTION", True)),
            driver=source_cfg.get("DRIVER", "ODBC Driver 17 for SQL Server"),
            timeout=int(source_cfg.get("TIMEOUT", 30)),
        )

        destination = SqlServerConnectionConfig(
            server=destination_cfg["SERVER"],
            database=destination_cfg["DATABASE"],
            username=destination_cfg.get("USERNAME", ""),
            password=destination_cfg.get("PASSWORD", ""),
            trusted_connection=bool(destination_cfg.get("TRUSTED_CONNECTION", True)),
            driver=destination_cfg.get("DRIVER", "ODBC Driver 17 for SQL Server"),
            timeout=int(destination_cfg.get("TIMEOUT", 30)),
        )

        return CostoProdDetalleETLConfig(
            source=source,
            destination=destination,
            source_table=etl_settings["SOURCE_TABLE"],
            destination_table=etl_settings["DESTINATION_TABLE"],
            destination_date_column=etl_settings.get("DESTINATION_DATE_COLUMN", "fecha_fin_mes"),
            hatcheries=hatcheries,
            species_type=int(etl_settings.get("SPECIES_TYPE", 1)),
            farm_type=int(etl_settings.get("FARM_TYPE", 2)),
        )
