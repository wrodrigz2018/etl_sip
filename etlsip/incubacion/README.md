# ETL Incubación: Documentación Operativa

## 1. Configuración inicial

### 1.1 Autenticación

La ETL soporta dos modos de autenticación:

**Opción A: Keycloak (Recomendado para producción)**
- Usa el servidor Keycloak corporativo
- Credenciales centralizadas
- Usuarios se sincronizan automáticamente

**Opción B: Autenticación Local (Desarrollo)**
- Usuarios locales en Django
- Sin dependencia externa
- Más simple para testing

Ver [KEYCLOAK.md](KEYCLOAK.md) para detalles de integración Keycloak.

Edita `etlsip/.env` con tus valores reales (la plantilla está en `etlsip/.env.example`):

```bash
# SQL Server source (origen de datos)
ETL_SOURCE_SERVER=192.168.3.26              # IP o nombre del servidor origen
ETL_SOURCE_DATABASE=Mtech_v7                # Base de datos origen
ETL_SOURCE_USERNAME=PRONACA\\genapi         # Usuario (si no usas Windows/AD)
ETL_SOURCE_PASSWORD=                        # Contraseña (si no usas Windows/AD)
ETL_SOURCE_TRUSTED_CONNECTION=true          # true=Windows/AD, false=SQL user
ETL_SOURCE_DRIVER=ODBC Driver 17 for SQL Server
ETL_SOURCE_TIMEOUT=30

# SQL Server destination (destino)
ETL_DEST_SERVER=1sq-pipbdd                  # IP o nombre del servidor destino
ETL_DEST_DATABASE=Mtech_v7                  # Base de datos destino
ETL_DEST_USERNAME=PRONACA\\genapi           # Usuario (si no usas Windows/AD)
ETL_DEST_PASSWORD=                          # Contraseña (si no usas Windows/AD)
ETL_DEST_TRUSTED_CONNECTION=true            # true=Windows/AD, false=SQL user
ETL_DEST_DRIVER=ODBC Driver 17 for SQL Server
ETL_DEST_TIMEOUT=30

# ETL mapping (tablas y columnas)
ETL_SOURCE_TABLE=mtech.mvProteinJournalTrans  # Tabla origen completa
ETL_DEST_TABLE=mtech.mvProteinJournalTrans_incubacion  # Tabla destino (debe existir)
ETL_DEST_DATE_COLUMN=xDate                    # Columna de fecha en destino
ETL_SOURCE_CODES=EOP B-HIM - Hatcher,EOP B-HIM - Allocations  # Códigos a filtrar
```

**⚠️ Nota:** `ETL_DEST_TABLE` debe existir en el servidor destino con la misma estructura de columnas que el origen.

### 1.2 Instalar dependencias

```bash
C:/Modelos/pollos/venv/Scripts/python.exe -m pip install -r etlsip/requirements.txt
```

## 2. Validación previa (Health Check)

Antes de ejecutar la ETL, valida conectividad y permisos:

```bash
C:/Modelos/pollos/venv/Scripts/python.exe etlsip/manage.py etl_health_check
```

**Salida esperada:**
```
======================================================================
ETL Health Check
======================================================================

[1/4] Checking SOURCE connectivity...
✓ SOURCE connected: 192.168.3.26 / Mtech_v7

[2/4] Checking DESTINATION connectivity...
✓ DESTINATION connected: 1sq-pipbdd / Mtech_v7

[3/4] Checking SOURCE table readability...
✓ SOURCE table readable: mtech.mvProteinJournalTrans

[4/4] Checking DESTINATION table writeability...
✓ DESTINATION table accessible: mtech.mvProteinJournalTrans_incubacion

======================================================================
Health check PASSED. Ready to run ETL.
======================================================================
```

Si falla, verás detalles del error (conexión, permisos, tabla no existe, etc.).

## 3. Ejecutar ETL

### 3.1 Dry-run (prueba sin persistencia)

Extrae datos y muestra conteos sin borrar ni insertar nada:

```bash
C:/Modelos/pollos/venv/Scripts/python.exe etlsip/manage.py etl_incubacion \
  --start-date 2024-06-01 \
  --end-date 2024-06-30 \
  --dry-run
```

**Salida esperada:**
```
ETL completed. source_rows=1250, deleted_rows=0, inserted_rows=0, dry_run=True
```

### 3.2 Ejecución real (recarga completa para rango)

Borra registros en destino por rango de fechas e inserta nuevos:

```bash
C:/Modelos/pollos/venv/Scripts/python.exe etlsip/manage.py etl_incubacion \
  --start-date 2024-06-01 \
  --end-date 2024-06-30
```

**Salida esperada:**
```
ETL completed. source_rows=1250, deleted_rows=840, inserted_rows=1250, dry_run=False
```

### 3.3 Parámetros opcionales

- `--batch-size N`: Tamaño de lote para INSERT (defecto: 1000)
- `--dry-run`: Solo extrae sin persistir

Ejemplo con lotes más pequeños:

```bash
C:/Modelos/pollos/venv/Scripts/python.exe etlsip/manage.py etl_incubacion \
  --start-date 2024-06-01 \
  --end-date 2024-06-30 \
  --batch-size 500
```

## 4. Auditoría de corridas

Cada ejecución se registra en la tabla `incubacion_etlrunaudit`:

```bash
C:/Modelos/pollos/venv/Scripts/python.exe etlsip/manage.py shell
```

```python
from incubacion.models import ETLRunAudit

# Ver todas las corridas
for run in ETLRunAudit.objects.all():
    print(run)

# Ver última corrida
last = ETLRunAudit.objects.latest('started_at')
print(f"Status: {last.status}")
print(f"Source rows: {last.source_rows}")
print(f"Inserted rows: {last.inserted_rows}")
print(f"Error: {last.error_message}")
```

También puedes verlas en el admin de Django:

```bash
C:/Modelos/pollos/venv/Scripts/python.exe etlsip/manage.py createsuperuser
C:/Modelos/pollos/venv/Scripts/python.exe etlsip/manage.py runserver
# Accede a http://localhost:8000/admin/ y navega a Incubacion > ETL Run Audits
```

## 5. Estructura de la app

```
incubacion/
├── admin.py                     # Admin para ver corridas
├── apps.py                      # Config de app
├── models.py                    # Modelo ETLRunAudit
├── services.py                  # Lógica ETL (conexión, extracción, carga)
├── management/
│   └── commands/
│       ├── etl_incubacion.py    # Comando principal de ETL
│       └── etl_health_check.py  # Validación de conectividad
└── migrations/
    └── 0001_initial.py          # Migración del modelo
```

## 6. Workflow recomendado

1. **Configurar .env** con valores reales
2. **Ejecutar health check** para validar conectividad
3. **Ejecutar dry-run** para revisar conteos esperados
4. **Ejecutar ETL real** para cargar datos
5. **Verificar auditoría** para confirmar resultado
6. **Repetir mismo rango** (recarga completa) para validar idempotencia

## 7. Comportamiento de recarga completa

Para un rango de fechas dado (ej: 2024-06-01 a 2024-06-30):

1. **Extrae** desde origen todos los registros del rango + filtros (HAT %, source codes)
2. **Borra** en destino todos los registros del rango (DELETE WHERE xDate BETWEEN ...)
3. **Inserta** los registros extraídos en lotes
4. **Transacción**: Si falla, hace rollback de todo (no borra sin insertar)

Si repites el mismo rango,:
- Borrará registros previos del rango
- Insertará nuevamente los datos
- **Resultado**: No hay duplicados, solo datos actuales

## 8. Troubleshooting

### Error: "Empty ETL_INCUBACION setting: DESTINATION_TABLE"
→ Completa `ETL_DEST_TABLE` en `.env`

### Error: "Source connection failed: login failed"
→ Valida credenciales SQL Server, usuario y contraseña en `.env`, y configuración de Windows/AD

### Error: "Source table access failed: ... not found"
→ Valida que la tabla origen existe: `SELECT * FROM mtech.mvProteinJournalTrans`

### Error: "DESTINATION table access failed"
→ Valida que la tabla destino existe y tienes permisos de lectura/escritura

### El dry-run muestra 0 filas
→ Los filtros (HAT %, source codes, rango de fechas) podrían estar muy restrictivos
→ Prueba ampliar el rango de fechas o revisar si hay datos en origen

## 9. Próximos pasos

- Automatizar con un scheduler (ej: Windows Task Scheduler, cron en Linux)
- Mejorar transformación de datos si es necesaria
- Expandir a otras apps más allá de incubacion
