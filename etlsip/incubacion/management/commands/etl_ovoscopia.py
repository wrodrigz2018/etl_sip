from __future__ import annotations

from datetime import date, datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from incubacion.services import OvoscopiaETLConfig, SqlServerConnectionConfig, run_etl_ovoscopia


class Command(BaseCommand):
    help = "Import Ovoscopia data from Mtech_v7 to HtcZoo"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--start-date", required=True, help="Start date in YYYY-MM-DD format")
        parser.add_argument("--end-date", required=True, help="End date in YYYY-MM-DD format")
        parser.add_argument("--dry-run", action="store_true", help="Extract only without changing destination")
        parser.add_argument("--batch-size", type=int, default=1000)

    def handle(self, *args, **options) -> None:
        start_date = self._parse_date(options["start_date"], "start-date")
        end_date = self._parse_date(options["end_date"], "end-date")
        if end_date < start_date:
            raise CommandError("--end-date must be greater than or equal to --start-date")
        if options["batch_size"] <= 0:
            raise CommandError("--batch-size must be greater than zero")
        try:
            result = run_etl_ovoscopia(self._build_config(), start_date, end_date, options["dry_run"], options["batch_size"])
        except Exception as exc:
            raise CommandError(f"ETL Ovoscopia failed: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(
            f"ETL completed. source_rows={result['source_rows']}, "
            f"deleted_rows={result['deleted_rows']}, inserted_rows={result['inserted_rows']}, "
            f"dry_run={options['dry_run']}"
        ))

    @staticmethod
    def _parse_date(value: str, argument_name: str) -> date:
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError as exc:
            raise CommandError(f"--{argument_name} must use YYYY-MM-DD format") from exc

    @staticmethod
    def _build_config() -> OvoscopiaETLConfig:
        cfg = settings.ETL_OVOSCOPIA

        def connection(section: str) -> SqlServerConnectionConfig:
            values = cfg[section]
            return SqlServerConnectionConfig(
                server=values["SERVER"], database=values["DATABASE"],
                username=values.get("USERNAME", ""), password=values.get("PASSWORD", ""),
                trusted_connection=bool(values.get("TRUSTED_CONNECTION", True)),
                driver=values.get("DRIVER", "ODBC Driver 17 for SQL Server"),
                timeout=int(values.get("TIMEOUT", 30)),
            )

        return OvoscopiaETLConfig(
            source=connection("SOURCE"), destination=connection("DESTINATION"),
            destination_table=cfg.get("DESTINATION_TABLE", "dbo.Ovoscopia"),
        )