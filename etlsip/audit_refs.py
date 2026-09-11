import os, pathlib
for p in pathlib.Path('.').rglob('*.py'):
 s=p.read_text(encoding='utf-8',errors='ignore')
 if 'Mtech_v7' in s or '192.168.3.26' in s or 'pyodbc' in s or 'DATABASES' in s:
  print('FILE',p)
  for i,l in enumerate(s.splitlines(),1):
   if any(x in l for x in ['Mtech_v7','192.168.3.26','pyodbc','DATABASES','OPTIONS','ODBC','DRIVER']): print(i, l[:300])
