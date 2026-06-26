"""Check available date range in source table."""
from django.core.management.base import BaseCommand
from django.conf import settings
from incubacion.services import SqlServerConnectionConfig, open_connection


class Command(BaseCommand):
    help = 'Check date range available in source table'

    def handle(self, *args, **options):
        config_dict = settings.ETL_INCUBACION
        
        source_config = SqlServerConnectionConfig(
            server=config_dict['SOURCE']['SERVER'],
            database=config_dict['SOURCE']['DATABASE'],
            username=config_dict['SOURCE']['USERNAME'],
            password=config_dict['SOURCE']['PASSWORD'],
            trusted_connection=config_dict['SOURCE']['TRUSTED_CONNECTION'],
            driver=config_dict['SOURCE']['DRIVER'],
            timeout=config_dict['SOURCE']['TIMEOUT'],
        )

        source_conn = open_connection(source_config)
        try:
            cursor = source_conn.cursor()
            
            # Check date range
            query = f"""
            SELECT 
                MIN(xDate) as min_date,
                MAX(xDate) as max_date,
                COUNT(*) as total_rows
            FROM {config_dict['SOURCE_TABLE']}
            WHERE SourceCode IN ({', '.join(f"'{code}'" for code in config_dict['SOURCE_CODES'])})
            """
            
            self.stdout.write(self.style.SUCCESS('\n📅 Date Range in Source Table'))
            self.stdout.write('-' * 60)
            
            cursor.execute(query)
            row = cursor.fetchone()
            
            if row:
                min_date, max_date, total = row
                self.stdout.write(f"Min Date: {min_date}")
                self.stdout.write(f"Max Date: {max_date}")
                self.stdout.write(f"Total Rows: {total}")
                
                if min_date and max_date:
                    self.stdout.write(f"\n✓ Try with: --start-date {min_date.date()} --end-date {max_date.date()}")
            else:
                self.stdout.write(self.style.WARNING("No data found in source table"))
            
            cursor.close()
        finally:
            source_conn.close()
        
        self.stdout.write("")
