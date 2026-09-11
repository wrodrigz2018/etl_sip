import os, inspect, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','etlsip.settings'); django.setup()
import incubacion.services as s
from django.conf import settings
print('SERVICE_CONFIG_NAMES', [n for n in dir(s) if 'config' in n.lower() or 'connection' in n.lower()])
for n in ['SqlServerConnectionConfig','open_connection','build_ovoscopia_extract_query']:
 o=getattr(s,n,None); print(n, inspect.signature(o) if o else None)
for n in dir(settings):
 if 'OVOS' in n or 'DATABASE' in n:
  v=getattr(settings,n)
  if isinstance(v,dict): print('SETTING',n, {k:('***' if any(x in k.upper() for x in ['PASS','USER','UID','PWD']) else v[k]) for k in v})
