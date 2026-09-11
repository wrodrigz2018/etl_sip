import os, inspect, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','etlsip.settings')
django.setup()
from incubacion.services import build_ovoscopia_extract_query
from django.conf import settings
print('SIGNATURE', inspect.signature(build_ovoscopia_extract_query))
print('SOURCE_START')
print(inspect.getsource(build_ovoscopia_extract_query))
print('ALIASES', list(settings.DATABASES))
for a,c in settings.DATABASES.items():
    print('DB',a,'ENGINE',c.get('ENGINE'),'NAME',c.get('NAME'),'HOST',c.get('HOST'))
