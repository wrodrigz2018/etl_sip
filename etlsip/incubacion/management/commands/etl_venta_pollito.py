from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from incubacion.services import (
    SqlServerConnectionConfig,
    VentaPollitoETLConfig,
    run_etl_venta_pollito,
)


class Command(BaseCommand):
    help = "Import venta-pollito.xlsx into SQL Server dbo.VentaPollito"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--excel-path", default="", help="Path to the venta-pollito Excel file")
        parser.add_argument("--dry-run", action="store_true", help="Validate and transform without database changes")
        parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for INSERT operations")

    def handle(self, *args, **options) -> None:
        batch_size = options["batch_size"]
        if batch_size <= 0:
            raise CommandError("--batch-size must be greater than zero")

        config, excel_path = self._build_config(options.get("excel_path") or "")
        try:
            result = run_etl_venta_pollito(
                config=config,
                excel_path=excel_path,
                dry_run=options["dry_run"],
                batch_size=batch_size,
            )
        except Exception as exc:
            raise CommandError(f"ETL venta pollito failed: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(
            "ETL venta pollito completed. "
            f"source_rows={result['source_rows']}, "
            f"deleted_rows={result['deleted_rows']}, "
            f"inserted_rows={result['inserted_rows']}, "
            f"dry_run={options['dry_run']}"
        ))
        self.stdout.write(f"Summary: {result['summary']}")

    @staticmethod
    def _build_config(excel_path_override: str) -> tuple[VentaPollitoETLConfig, str]:
        etl_settings = getattr(settings, "ETL_VENTA_POLLITO", None)
        if not etl_settings:
            raise CommandError("ETL_VENTA_POLLITO settings are missing")

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
        return VentaPollitoETLConfig(
            destination=destination,
            destination_table=etl_settings.get("DESTINATION_TABLE", "dbo.VentaPollito"),
            sheet_data=etl_settings.get("SHEET_DATA", "Hoja1"),
        ), excel_path_override or str(etl_settings["EXCEL_PATH"])
