# Autenticación local en ETL

## Descripción

La autenticación de ETL usa exclusivamente los usuarios locales de Django. Keycloak ya no participa en el inicio de sesión.

## Configuración

## Flujo de Autenticación

1. Usuario ingresa credenciales en `/etl/login/`
2. Sistema valida contra base de datos Django
3. Si válido:
   - Inicia sesión y redirige a dashboard
4. Si inválido:
   - Muestra error: "Usuario o contraseña incorrectos"

## Crear Usuarios Locales

Usa el comando de management:

```bash
C:/Modelos/pollos/venv/Scripts/python.exe etlsip/manage.py create_etl_user usuario1 --password pass123
```

## Archivos Modificados

- [etlsip/incubacion/views.py](../incubacion/views.py) — Vista de autenticación local
- [etlsip/etlsip/settings.py](../etlsip/settings.py) — Configuración del proyecto
- [etlsip/requirements.txt](../requirements.txt) — Dependencias del proyecto

## Troubleshooting

### Usuario o contraseña incorrectos

Verifica que el usuario exista en Django y restablece su contraseña con `create_etl_user` si es necesario.

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
