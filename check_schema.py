#!/usr/bin/env python
"""Check table structure for decimal precision issues."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'etlsip.settings')

import django
django.setup()

from django.conf import settings
from incubacion.services import open_connection

config = settings.ETL_INCUBACION

print("=" * 80)
print("ORIGIN TABLE STRUCTURE")
print("=" * 80)

source_conn = open_connection(config['SOURCE'])
cursor = source_conn.cursor()

# Get column info from origin
query = f"""
SELECT COLUMN_NAME, DATA_TYPE, NUMERIC_PRECISION, NUMERIC_SCALE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'mtech' AND TABLE_NAME = 'mvProteinJournalTrans'
ORDER BY ORDINAL_POSITION
"""

print(f"\nQuery: {query}\n")
cursor.execute(query)
print("COLUMN_NAME".ljust(30) + "DATA_TYPE".ljust(20) + "PRECISION".ljust(15) + "SCALE")
print("-" * 80)

for row in cursor.fetchall():
    col_name, data_type, precision, scale = row
    precision_str = str(precision) if precision else "-"
    scale_str = str(scale) if scale else "-"
    print(f"{col_name[:29]:<30}{data_type[:19]:<20}{precision_str:<15}{scale_str}")

source_conn.close()

print("\n" + "=" * 80)
print("DESTINATION TABLE STRUCTURE")
print("=" * 80)

dest_conn = open_connection(config['DESTINATION'])
cursor = dest_conn.cursor()

# Get column info from destination
query = f"""
SELECT COLUMN_NAME, DATA_TYPE, NUMERIC_PRECISION, NUMERIC_SCALE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'ProteinJournal_Staging'
ORDER BY ORDINAL_POSITION
"""

print(f"\nQuery: {query}\n")
cursor.execute(query)
print("COLUMN_NAME".ljust(30) + "DATA_TYPE".ljust(20) + "PRECISION".ljust(15) + "SCALE")
print("-" * 80)

for row in cursor.fetchall():
    col_name, data_type, precision, scale = row
    precision_str = str(precision) if precision else "-"
    scale_str = str(scale) if scale else "-"
    print(f"{col_name[:29]:<30}{data_type[:19]:<20}{precision_str:<15}{scale_str}")

dest_conn.close()

print("\n" + "=" * 80)
print("COMPARISON: MISMATCHES")
print("=" * 80)
