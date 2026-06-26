"""Check which columns in destination allow nulls."""
from django.core.management.base import BaseCommand
from django.conf import settings
from incubacion.services import SqlServerConnectionConfig, open_connection


class Command(BaseCommand):
    help = 'Check which columns allow nulls in destination table'

    def handle(self, *args, **options):
        config_dict = settings.ETL_INCUBACION
        
        dest_config = SqlServerConnectionConfig(
            server=config_dict['DESTINATION']['SERVER'],
            database=config_dict['DESTINATION']['DATABASE'],
            username=config_dict['DESTINATION']['USERNAME'],
            password=config_dict['DESTINATION']['PASSWORD'],
            trusted_connection=config_dict['DESTINATION']['TRUSTED_CONNECTION'],
            driver=config_dict['DESTINATION']['DRIVER'],
            timeout=config_dict['DESTINATION']['TIMEOUT'],
        )

        dest_conn = open_connection(dest_config)
        try:
            cursor = dest_conn.cursor()
            
            query = """
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'ProteinJournal_Staging'
            ORDER BY ORDINAL_POSITION
            """
            
            self.stdout.write(self.style.SUCCESS('\n📋 Destination Columns (Nullable Check)'))
            self.stdout.write('-' * 80)
            self.stdout.write("COLUMN_NAME".ljust(30) + "DATA_TYPE".ljust(20) + "NULLABLE")
            self.stdout.write('-' * 80)
            
            cursor.execute(query)
            for row in cursor.fetchall():
                col_name, data_type, is_nullable = row
                nullable_str = "✓ YES" if is_nullable == 'YES' else "✗ NO"
                style = self.style.SUCCESS if is_nullable == 'YES' else self.style.ERROR
                self.stdout.write(style(f"{col_name[:29]:<30}{data_type[:19]:<20}{nullable_str}"))
            
            cursor.close()
        finally:
            dest_conn.close()
        
        self.stdout.write("")
