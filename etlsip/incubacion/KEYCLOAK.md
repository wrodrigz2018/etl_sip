# Integración Keycloak en ETL

## Descripción

La autenticación de ETL ahora soporta **Keycloak** como proveedor de identidad, con fallback a autenticación local (Django) si Keycloak está deshabilitado.

## Configuración

### 1. Variables de Entorno

Edita [etlsip/.env](../.env) con los valores de tu servidor Keycloak:

```env
# Keycloak
KEYCLOAK_SERVER=https://cdkcpro.pronaca.com/auth/
KEYCLOAK_CLIENT_ID=sip
KEYCLOAK_REALM=pronaca-gb
USE_KEYCLOAK=true
```

**Notas:**
- `KEYCLOAK_SERVER`: URL del servidor Keycloak (incluye `/auth/`)
- `KEYCLOAK_CLIENT_ID`: ID del cliente configurado en Keycloak
- `KEYCLOAK_REALM`: Nombre del realm en Keycloak
- `USE_KEYCLOAK`: `true` para habilitar Keycloak, `false` para usar autenticación local

### 2. Dependencias

Las dependencias están en [requirements.txt](../requirements.txt):

```
python-keycloak>=3.8.0
```

Instala si no lo hiciste:
```bash
C:/Modelos/pollos/venv/Scripts/python.exe -m pip install python-keycloak
```

## Flujo de Autenticación

### Cuando USE_KEYCLOAK=true (Keycloak habilitado)

1. Usuario ingresa credenciales en `/etl/login/`
2. Sistema valida contra servidor Keycloak
3. Si válido:
   - Crea o actualiza usuario en Django
   - Agrega usuario al grupo `etl_executor`
   - Inicia sesión y redirige a dashboard
4. Si inválido:
   - Muestra error: "Usuario o contraseña incorrectos en Keycloak"

### Cuando USE_KEYCLOAK=false (Autenticación local)

1. Usuario ingresa credenciales en `/etl/login/`
2. Sistema valida contra base de datos Django
3. Si válido:
   - Inicia sesión y redirige a dashboard
4. Si inválido:
   - Muestra error: "Usuario o contraseña incorrectos"

## Crear Usuarios en Keycloak

Los usuarios se crean automáticamente en Django cuando:
1. Se autentican exitosamente contra Keycloak
2. No existen aún en la base de datos Django

Los datos se sincronizan desde Keycloak:
- **username** (preferred_username)
- **email**
- **first_name** (given_name)
- **last_name** (family_name)

## Crear Usuarios Locales (sin Keycloak)

Si USE_KEYCLOAK=false, usa el comando de management:

```bash
C:/Modelos/pollos/venv/Scripts/python.exe etlsip/manage.py create_etl_user usuario1 --password pass123
```

## Archivos Modificados

- [etlsip/incubacion/auth.py](../incubacion/auth.py) — Módulo de autenticación Keycloak
- [etlsip/incubacion/views.py](../incubacion/views.py) — Vistas actualizadas con soporte Keycloak
- [etlsip/etlsip/settings.py](../etlsip/settings.py) — Configuración Keycloak
- [etlsip/.env](../.env) — Variables de entorno Keycloak
- [etlsip/requirements.txt](../requirements.txt) — Dependencia python-keycloak

## Troubleshooting

### Error: "Usuario o contraseña incorrectos en Keycloak"

**Causas posibles:**
1. Credenciales inválidas en Keycloak
2. Servidor Keycloak no accesible
3. Client ID o Realm incorrecto

**Solución:**
- Verifica credenciales en el servidor Keycloak
- Confirma que KEYCLOAK_SERVER, KEYCLOAK_CLIENT_ID y KEYCLOAK_REALM son correctos
- Prueba conectividad: `ping cdkcpro.pronaca.com`

### Error: Timeout conectando a Keycloak

**Causas posibles:**
1. Servidor Keycloak caído
2. Problema de conectividad de red
3. Firewall bloqueando puerto HTTPS

**Solución:**
- Verifica que el servidor Keycloak esté en línea
- Confirma conectividad de red hacia `cdkcpro.pronaca.com:443`
- Si falla persistentemente, deshabilita Keycloak: `USE_KEYCLOAK=false`

### Cambiar de Keycloak a Autenticación Local

1. Edita [etlsip/.env](../.env):
   ```env
   USE_KEYCLOAK=false
   ```

2. Reinicia el servidor Django

3. Los usuarios creados en Keycloak seguirán existiendo en Django

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

⚠️ **Nunca guardes credenciales Keycloak en el código.** Siempre usa variables de entorno.

✅ **Mejores prácticas:**
1. `.env` es local (no se sube a control de versiones)
2. `.env.example` contiene plantilla sin credenciales reales
3. Credenciales se cargan automáticamente al iniciar Django
4. Las contraseñas de usuarios se hashean en Django
