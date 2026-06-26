"""Preview ETL data before execution."""
from django.core.management.base import BaseCommand
from django.conf import settings
from incubacion.services import (
    SqlServerConnectionConfig,
    IncubacionETLConfig,
    extract_rows,
    open_connection,
    get_destination_columns,
    map_columns_and_rows,
)
from datetime import datetime


class Command(BaseCommand):
    help = 'Preview ETL data that will be transferred'

    def add_arguments(self, parser):
        parser.add_argument('--start-date', type=str, required=True, help='Start date (YYYY-MM-DD)')
        parser.add_argument('--end-date', type=str, required=True, help='End date (YYYY-MM-DD)')
        parser.add_argument('--limit', type=int, default=10, help='Max rows to preview (default: 10)')

    def _parse_date(self, date_str: str):
        """Parse date string YYYY-MM-DD."""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")

    def handle(self, *args, **options):
        config_dict = settings.ETL_INCUBACION
        
        start_date = self._parse_date(options['start_date'])
        end_date = self._parse_date(options['end_date'])
        limit = options['limit']
        
        if end_date < start_date:
            self.stdout.write(self.style.ERROR('❌ End date must be >= start date'))
            return

        # Build config objects
        source_config = SqlServerConnectionConfig(
            server=config_dict['SOURCE']['SERVER'],
            database=config_dict['SOURCE']['DATABASE'],
            username=config_dict['SOURCE']['USERNAME'],
            password=config_dict['SOURCE']['PASSWORD'],
            trusted_connection=config_dict['SOURCE']['TRUSTED_CONNECTION'],
            driver=config_dict['SOURCE']['DRIVER'],
            timeout=config_dict['SOURCE']['TIMEOUT'],
        )

        dest_config = SqlServerConnectionConfig(
            server=config_dict['DESTINATION']['SERVER'],
            database=config_dict['DESTINATION']['DATABASE'],
            username=config_dict['DESTINATION']['USERNAME'],
            password=config_dict['DESTINATION']['PASSWORD'],
            trusted_connection=config_dict['DESTINATION']['TRUSTED_CONNECTION'],
            driver=config_dict['DESTINATION']['DRIVER'],
            timeout=config_dict['DESTINATION']['TIMEOUT'],
        )

        etl_config = IncubacionETLConfig(
            source=source_config,
            destination=dest_config,
            source_table=config_dict['SOURCE_TABLE'],
            destination_table=config_dict['DESTINATION_TABLE'],
            destination_date_column=config_dict['DESTINATION_DATE_COLUMN'],
            source_codes=tuple(config_dict['SOURCE_CODES']),
        )

        # Extract data
        self.stdout.write(self.style.SUCCESS('\n✓ Extracting data...'))
        source_conn = open_connection(source_config)
        try:
            source_columns, source_rows = extract_rows(
                source_conn=source_conn,
                source_table=etl_config.source_table,
                start_date=start_date,
                end_date=end_date,
                source_codes=etl_config.source_codes,
            )
        finally:
            source_conn.close()

        # Get destination columns and map
        dest_conn = open_connection(dest_config)
        try:
            dest_columns = get_destination_columns(dest_conn, etl_config.destination_table)
        finally:
            dest_conn.close()

        # Map columns
        mapped_columns, mapped_rows = map_columns_and_rows(
            source_columns, source_rows, dest_columns
        )

        # Display summary
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
        self.stdout.write(self.style.SUCCESS('DATA PREVIEW'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        
        self.stdout.write(f"\nDate Range: {start_date} → {end_date}")
        self.stdout.write(f"Source Codes: {', '.join(etl_config.source_codes)}")
        self.stdout.write(f"\nTotal rows found in source: {len(source_rows)}")
        self.stdout.write(f"Columns to transfer: {len(mapped_columns)}/{len(source_columns)}")
        
        # Show mapped columns
        self.stdout.write(self.style.SUCCESS(f'\n📋 Columns to transfer ({len(mapped_columns)}):'))
        self.stdout.write('-' * 80)
        for col in mapped_columns:
            self.stdout.write(f"  • {col}")

        # Show sample data
        if mapped_rows:
            self.stdout.write(self.style.SUCCESS(f'\n📊 Sample data (first {min(limit, len(mapped_rows))} rows):'))
            self.stdout.write('-' * 80)
            
            # Print headers
            header = " | ".join(col[:15].ljust(15) for col in mapped_columns)
            self.stdout.write(header)
            self.stdout.write('-' * 80)
            
            # Print rows
            for row in mapped_rows[:limit]:
                values = []
                for val in row:
                    if val is None:
                        val_str = "NULL"
                    elif isinstance(val, (int, float)):
                        val_str = str(val)[:15]
                    else:
                        val_str = str(val)[:15]
                    values.append(val_str.ljust(15))
                self.stdout.write(" | ".join(values))
        else:
            self.stdout.write(self.style.WARNING('\n⚠️  No rows found for this date range'))

        self.stdout.write(self.style.SUCCESS('\n✓ Preview complete\n'))
