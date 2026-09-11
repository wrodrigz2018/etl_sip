import os, json, math, datetime, decimal, numbers, inspect
os.environ.setdefault('DJANGO_SETTINGS_MODULE','etlsip.settings')
import django; django.setup()
import pyodbc
from django.conf import settings
from incubacion.services import build_ovoscopia_extract_query, open_connection, SqlServerConnectionConfig

cfg = settings.ETL_OVOSCOPIA

def make(c):
    return SqlServerConnectionConfig(server=c['SERVER'], database=c['DATABASE'], username=c.get('USERNAME',''), password=c.get('PASSWORD',''), trusted_connection=c.get('TRUSTED_CONNECTION',True), driver=c.get('DRIVER','ODBC Driver 17 for SQL Server'), timeout=c.get('TIMEOUT',30))
source = open_connection(make(cfg['SOURCE']))
dest = open_connection(make(cfg['DESTINATION']))
try:
    q = build_ovoscopia_extract_query()
    cur = source.cursor(); cur.execute(q, (datetime.date(2026,8,30), datetime.date(2026,9,6)))
    desc = cur.description
    rows = cur.fetchall()
    def tc(v):
        try: name=v.__name__
        except Exception: name=None
        return {'repr':repr(v), 'name':name}
    def avail(v): return v if v is not None else None
    metadata=[]
    for i,d in enumerate(desc,1):
        metadata.append({'ordinal':i,'alias':d[0],'type_code':tc(d[1]),'display_size':avail(d[2]),'internal_size':avail(d[3]),'precision':avail(d[4]),'scale':avail(d[5])})
    observed=[]
    for j,d in enumerate(desc):
        vals=[r[j] for r in rows if r[j] is not None]
        types=sorted({type(v).__name__ for v in vals})
        item={'ordinal':j+1,'alias':d[0],'python_types':types,'nonnull_count':len(vals)}
        if any(isinstance(v,(str,bytes,bytearray)) for v in vals):
            sv=[v for v in vals if isinstance(v,(str,bytes,bytearray))]
            lens=[len(v) for v in sv]
            item['max_string_length']=max(lens) if lens else 0
            item['masked_example']=f'<string len={max(lens) if lens else 0} masked>'
        nums=[v for v in vals if isinstance(v,numbers.Number) and not isinstance(v,(bool,complex))]
        if nums:
            item['numeric_min']=min(nums); item['numeric_max']=max(nums)
        observed.append(item)
    mcur=dest.cursor()
    mcur.execute("""SELECT c.COLUMN_NAME, c.DATA_TYPE, c.CHARACTER_MAXIMUM_LENGTH, c.NUMERIC_PRECISION, c.NUMERIC_SCALE, c.IS_NULLABLE, c.ORDINAL_POSITION FROM INFORMATION_SCHEMA.COLUMNS c WHERE c.TABLE_SCHEMA=? AND c.TABLE_NAME=? ORDER BY c.ORDINAL_POSITION""", ('dbo','Ovoscopia'))
    drows=mcur.fetchall()
    # sys metadata explicitly requested; not printed separately if same fields, retain audit evidence
    scur=dest.cursor(); scur.execute("""SELECT c.name, t.name, c.max_length, c.precision, c.scale, c.is_nullable, c.column_id FROM sys.columns c JOIN sys.types t ON c.user_type_id=t.user_type_id JOIN sys.objects o ON c.object_id=o.object_id JOIN sys.schemas s ON o.schema_id=s.schema_id WHERE s.name=? AND o.name=? ORDER BY c.column_id""", ('dbo','Ovoscopia'))
    srows=scur.fetchall()
    destmeta=[{'column':r[0],'type':r[1],'max_length':r[2],'precision':r[3],'scale':r[4],'nullable':bool(r[5]),'ordinal':r[6]} for r in drows]
    sysmeta=[{'column':r[0],'type':r[1],'max_length':r[2],'precision':r[3],'scale':r[4],'nullable':bool(r[5]),'ordinal':r[6]} for r in srows]
    bysrc={x['alias'].lower():x for x in observed}; bydesc={x['alias'].lower():x for x in metadata}; byd={x['column'].lower():x for x in destmeta}
    comparisons=[]
    for a in metadata:
        n=a['alias']; d=byd.get(n.lower()); o=bysrc[n.lower()]
        issues=[]
        if not d: issues.append('missing_destination_column')
        else:
            if 'max_string_length' in o and d['max_length'] not in (None,-1):
                lim=d['max_length']; lim = lim//2 if str(d['type']).lower() in ('nvarchar','nchar') else lim
                if o['max_string_length']>lim: issues.append(f'length_observed>{lim}')
            if 'max_string_length' in o and d['type'].lower() not in ('varchar','nvarchar','char','nchar','text','ntext'): issues.append('source_text_vs_destination_nontext')
        comparisons.append({'alias':n,'destination':d,'issues':issues})
    # aggregate additional source proof: one aggregate query over the exact full SELECT, only counts
    aggregate={}
    text_candidates=[x for x in observed if 'max_string_length' in x]
    if text_candidates:
        selects=[]
        for x in text_candidates:
            d=byd.get(x['alias'].lower()); lim=None
            if d and d['max_length'] not in (None,-1): lim=d['max_length']//2 if d['type'].lower() in ('nvarchar','nchar') else d['max_length']
            if lim is not None: selects.append(f"SUM(CASE WHEN [{x['alias']}] IS NOT NULL AND LEN([{x['alias']}]) > {int(lim)} THEN 1 ELSE 0 END) AS [{x['alias']}_over]")
        if selects:
            aq='SELECT '+', '.join(selects)+' FROM ('+q+') AS extract_rows'
            ac=source.cursor(); ac.execute(aq,(datetime.date(2026,8,30),datetime.date(2026,9,6))); ar=ac.fetchone()
            aggregate={text_candidates[i]['alias']: ar[i] for i in range(len(selects))}
    report={'range':{'start_inclusive':'2026-08-30','end_exclusive':'2026-09-06'},'source_row_count':len(rows),'source_cursor_description':metadata,'source_observed':observed,'destination_information_schema':destmeta,'destination_sys_columns_types':sysmeta,'comparisons':comparisons,'aggregate_counts_over_destination_limit':aggregate}
    print(json.dumps(report,ensure_ascii=False,default=str,indent=2))
finally:
    source.close(); dest.close()
