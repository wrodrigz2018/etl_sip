from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from incubacion.management.commands.etl_incubacion import Command as ETLCommand
from incubacion.services import open_connection


class Command(BaseCommand):
    help = "Validate connectivity and permissions to ETL source and destination SQL Servers"

    def handle(self, *args, **options) -> None:
        config = self._get_config()

        self.stdout.write("=" * 70)
        self.stdout.write(self.style.HTTP_INFO("ETL Health Check"))
        self.stdout.write("=" * 70)

        errors = []

        # Check source connectivity
        self.stdout.write("\n[1/4] Checking SOURCE connectivity...")
        try:
            source_conn = open_connection(config.source)
            cursor = source_conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            source_conn.close()
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ SOURCE connected: {config.source.server} / {config.source.database}"
                )
            )
        except Exception as exc:
            msg = f"✗ SOURCE connection failed: {exc}"
            self.stdout.write(self.style.ERROR(msg))
            errors.append(msg)

        # Check destination connectivity
        self.stdout.write("\n[2/4] Checking DESTINATION connectivity...")
        try:
            dest_conn = open_connection(config.destination)
            cursor = dest_conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            dest_conn.close()
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ DESTINATION connected: {config.destination.server} / {config.destination.database}"
                )
            )
        except Exception as exc:
            msg = f"✗ DESTINATION connection failed: {exc}"
            self.stdout.write(self.style.ERROR(msg))
            errors.append(msg)

        # Check source table readable
        self.stdout.write("\n[3/4] Checking SOURCE table readability...")
        try:
            source_conn = open_connection(config.source)
            cursor = source_conn.cursor()
            cursor.execute(f"SELECT TOP 1 * FROM {config.source_table}")
            cursor.close()
            source_conn.close()
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ SOURCE table readable: {config.source_table}"
                )
            )
        except Exception as exc:
            msg = f"✗ SOURCE table read failed: {exc}"
            self.stdout.write(self.style.ERROR(msg))
            errors.append(msg)

        # Check destination table writable
        self.stdout.write("\n[4/4] Checking DESTINATION table writeability...")
        try:
            dest_conn = open_connection(config.destination)
            cursor = dest_conn.cursor()
            cursor.execute(
                f"SELECT TOP 1 * FROM {config.destination_table}"
            )
            cursor.close()
            dest_conn.close()
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ DESTINATION table accessible: {config.destination_table}"
                )
            )
        except Exception as exc:
            msg = f"✗ DESTINATION table access failed: {exc}"
            self.stdout.write(self.style.ERROR(msg))
            errors.append(msg)

        # Summary
        self.stdout.write("\n" + "=" * 70)
        if errors:
            self.stdout.write(self.style.ERROR(f"Health check FAILED ({len(errors)} error(s))"))
            self.stdout.write("\nIssues found:")
            for error in errors:
                self.stdout.write(f"  - {error}")
            raise CommandError("Health check failed. Fix issues and retry.")
        else:
            self.stdout.write(self.style.SUCCESS("Health check PASSED. Ready to run ETL."))
            self.stdout.write("=" * 70)

    @staticmethod
    def _get_config():
        return ETLCommand._build_config()
