# Autenticación con Keycloak en ETL

## Descripción

La autenticación de ETL valida usuario y contraseña contra Keycloak/Active Directory (`KeycloakAuthenticator`). Django **no** almacena ni compara ninguna contraseña local: la tabla `auth_user` solo guarda un registro "sombra" (email, nombre, grupos, permisos) para la sesión, con `set_unusable_password()`.

## Configuración

Variables en `.env` (ver `etlsip/.env.example`):

```bash
KEYCLOAK_SERVER=https://cdkcpro.pronaca.com/auth/
KEYCLOAK_CLIENT_ID=sip
KEYCLOAK_REALM=pronaca-gb
```

Estas se mapean a `settings.KEYCLOAK_CONFIG` en [etlsip/etlsip/settings.py](../etlsip/settings.py).

## Flujo de Autenticación

1. Usuario ingresa credenciales en `/etl/login/`.
2. `KeycloakAuthenticator.authenticate()` valida el usuario/contraseña directamente contra Keycloak/AD.
3. Si válido:
   - Se crea/actualiza el usuario local Django (`get_or_create` por `username`), sincronizando email, nombre y apellido, con `set_unusable_password()`.
   - Inicia sesión y redirige a dashboard.
4. Si inválido:
   - Muestra error: "Usuario o contraseña incorrectos".

## Gestión de Usuarios

Los usuarios y contraseñas se administran en Keycloak/AD, no en Django. El registro local se crea automáticamente en el primer login exitoso. Los grupos/permisos (`etl_executor`, etc.) sí se gestionan localmente en Django tras la creación del usuario.

## Archivos Modificados

- [etlsip/incubacion/views.py](../incubacion/views.py) — Vista de autenticación contra Keycloak
- [etlsip/incubacion/auth.py](../incubacion/auth.py) — `KeycloakAuthenticator`
- [etlsip/etlsip/settings.py](../etlsip/settings.py) — Configuración del proyecto (`KEYCLOAK_CONFIG`)
- [etlsip/requirements.txt](../requirements.txt) — Dependencias del proyecto

## Troubleshooting

### Usuario o contraseña incorrectos

Verifica que el usuario y la contraseña sean válidos directamente en Keycloak/AD (no en Django). Revisa también conectividad al `KEYCLOAK_SERVER` y que `KEYCLOAK_CLIENT_ID`/`KEYCLOAK_REALM` sean correctos.

## Monitoreo

Para revisar quién se autenticó y cuándo, usa el admin de Django:

```bash
C:/Modelos/pollos/venv/Scripts/python.exe etlsip/manage.py runserver
# http://localhost:8000/admin/ → Users
```

O en el shell de Django:

```bash
C:/Modelos/pollos/venv/Scripts/python.exe etlsip/manage.py shell
```

```python
from django.contrib.auth.models import User
User.objects.all()  # Ver todos los usuarios
User.objects.get(username='admin').groups.all()  # Ver grupos de un usuario
```

## Seguridad

**Mejores prácticas:**
1. `.env` es local (no se sube a control de versiones)
2. `.env.example` contiene plantilla sin credenciales reales
3. Credenciales se cargan automáticamente al iniciar Django
4. Las contraseñas de usuarios se hashean en Django
