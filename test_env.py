import os
from dotenv import load_dotenv

load_dotenv('etlsip/.env')
use_keycloak = os.getenv('USE_KEYCLOAK')
print(f'USE_KEYCLOAK from .env: {use_keycloak}')
print(f'Type: {type(use_keycloak)}')
print(f'Bool value would be: {use_keycloak.lower() == "true" if use_keycloak else False}')
