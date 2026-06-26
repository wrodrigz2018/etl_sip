from django.core.management.base import BaseCommand
from django.conf import settings
from incubacion.services import open_connection, SqlServerConnectionConfig


class Command(BaseCommand):
    help = 'Check table schema for decimal precision mismatches'

    def handle(self, *args, **options):
        config = settings.ETL_INCUBACION

        source_config = SqlServerConnectionConfig(
            server=config['SOURCE']['SERVER'],
            database=config['SOURCE']['DATABASE'],
            username=config['SOURCE']['USERNAME'],
            password=config['SOURCE']['PASSWORD'],
            trusted_connection=config['SOURCE']['TRUSTED_CONNECTION'],
            driver=config['SOURCE']['DRIVER'],
            timeout=config['SOURCE']['TIMEOUT'],
        )

        dest_config = SqlServerConnectionConfig(
            server=config['DESTINATION']['SERVER'],
            database=config['DESTINATION']['DATABASE'],
            username=config['DESTINATION']['USERNAME'],
            password=config['DESTINATION']['PASSWORD'],
            trusted_connection=config['DESTINATION']['TRUSTED_CONNECTION'],
            driver=config['DESTINATION']['DRIVER'],
            timeout=config['DESTINATION']['TIMEOUT'],
        )

        print("\n" + "=" * 80)
        print("ORIGIN TABLE STRUCTURE")
        print("=" * 80)

        source_conn = open_connection(source_config)
        cursor = source_conn.cursor()

        query = """
        SELECT COLUMN_NAME, DATA_TYPE, NUMERIC_PRECISION, NUMERIC_SCALE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'mtech' AND TABLE_NAME = 'mvProteinJournalTrans'
        ORDER BY ORDINAL_POSITION
        """

        print(f"\nOrigin: {source_config.server}.{source_config.database}.mtech.mvProteinJournalTrans\n")
        cursor.execute(query)
        print("COLUMN_NAME".ljust(30) + "DATA_TYPE".ljust(20) + "PRECISION".ljust(15) + "SCALE")
        print("-" * 80)

        origin_cols = {}
        for row in cursor.fetchall():
            col_name, data_type, precision, scale = row
            precision_str = str(precision) if precision else "-"
            scale_str = str(scale) if scale else "-"
            origin_cols[col_name] = (data_type, precision, scale)
            print(f"{col_name[:29]:<30}{data_type[:19]:<20}{precision_str:<15}{scale_str}")

        source_conn.close()

        print("\n" + "=" * 80)
        print("DESTINATION TABLE STRUCTURE")
        print("=" * 80)

        dest_conn = open_connection(dest_config)
        cursor = dest_conn.cursor()

        query = """
        SELECT COLUMN_NAME, DATA_TYPE, NUMERIC_PRECISION, NUMERIC_SCALE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'ProteinJournal_Staging'
        ORDER BY ORDINAL_POSITION
        """

        print(f"\nDestination: {dest_config.server}.{dest_config.database}.dbo.ProteinJournal_Staging\n")
        cursor.execute(query)
        print("COLUMN_NAME".ljust(30) + "DATA_TYPE".ljust(20) + "PRECISION".ljust(15) + "SCALE")
        print("-" * 80)

        dest_cols = {}
        for row in cursor.fetchall():
            col_name, data_type, precision, scale = row
            precision_str = str(precision) if precision else "-"
            scale_str = str(scale) if scale else "-"
            dest_cols[col_name] = (data_type, precision, scale)
            print(f"{col_name[:29]:<30}{data_type[:19]:<20}{precision_str:<15}{scale_str}")

        dest_conn.close()

        # Check for precision mismatches
        print("\n" + "=" * 80)
        print("PRECISION MISMATCHES")
        print("=" * 80)
        
        mismatches = []
        for col_name in origin_cols:
            if col_name not in dest_cols:
                mismatches.append(f"⚠️  {col_name}: EXISTS IN ORIGIN BUT NOT IN DESTINATION")
                continue
            
            origin_type, origin_prec, origin_scale = origin_cols[col_name]
            dest_type, dest_prec, dest_scale = dest_cols[col_name]
            
            if origin_type != dest_type or origin_prec != dest_prec or origin_scale != dest_scale:
                mismatches.append(
                    f"⚠️  {col_name}: "
                    f"ORIGIN({origin_type}, P:{origin_prec}, S:{origin_scale}) "
                    f"→ DEST({dest_type}, P:{dest_prec}, S:{dest_scale})"
                )
        
        if mismatches:
            print(f"\nFound {len(mismatches)} mismatches:\n")
            for mismatch in mismatches:
                print(mismatch)
        else:
            print("\n✅ No mismatches found\n")
        
        print("\n✓ Schema check complete\n")


