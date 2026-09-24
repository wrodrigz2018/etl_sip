from __future__ import annotations

from datetime import date, datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError
from django.utils import timezone

from incubacion.models import ETLRunAudit
from incubacion.services import (
    ProdHuevosETLConfig,
    SqlServerConnectionConfig,
    run_etl_prod_huevos,
)


class Command(BaseCommand):
    help = "Run Produccion de Huevos ETL from SQL Server source to SQL Server destination"

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
        )

        try:
            result = run_etl_prod_huevos(
                config=config,
                start_date=start_date,
                end_date=end_date,
                dry_run=dry_run,
                batch_size=batch_size,
            )
            audit.source_rows = result["source_rows"]
            audit.deleted_rows = result["deleted_rows"]
            audit.inserted_rows = result["inserted_rows"]
            audit.ended_at = timezone.now()
            self._save_audit(audit)
        except Exception as exc:
            audit.status = ETLRunAudit.STATUS_FAILED
            audit.error_message = str(exc)
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
    def _build_config() -> ProdHuevosETLConfig:
        etl_settings = getattr(settings, "ETL_PROD_HUEVOS", None)
        if not etl_settings:
            raise CommandError("ETL_PROD_HUEVOS settings are missing")

        required_paths = [
            ("SOURCE", "SERVER"),
            ("SOURCE", "DATABASE"),
            ("DESTINATION", "SERVER"),
            ("DESTINATION", "DATABASE"),
            ("SOURCE_TABLE",),
            ("DESTINATION_TABLE",),
        ]

        for path in required_paths:
            current = etl_settings
            for key in path:
                if not isinstance(current, dict) or key not in current:
                    dotted = ".".join(path)
                    raise CommandError(f"Missing ETL_PROD_HUEVOS setting: {dotted}")
                current = current[key]
            if current in (None, ""):
                dotted = ".".join(path)
                raise CommandError(f"Empty ETL_PROD_HUEVOS setting: {dotted}")

        source_cfg = etl_settings["SOURCE"]
        destination_cfg = etl_settings["DESTINATION"]

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

        return ProdHuevosETLConfig(
            source=source,
            destination=destination,
            source_table=etl_settings["SOURCE_TABLE"],
            destination_table=etl_settings["DESTINATION_TABLE"],
            destination_date_column=etl_settings.get("DESTINATION_DATE_COLUMN", "Fecha"),
        )
