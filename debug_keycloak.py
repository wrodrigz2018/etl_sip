#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'etlsip.settings')
django.setup()

from django.conf import settings

print(f"DEBUG: USE_KEYCLOAK = {settings.USE_KEYCLOAK}")
print(f"DEBUG: KEYCLOAK_CONFIG = {settings.KEYCLOAK_CONFIG}")
print(f"DEBUG: _get_keycloak_authenticator would return: {settings.USE_KEYCLOAK}")
