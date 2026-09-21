# 🥚 ETL SIP — Sistema de Integración de Procesos

Panel web interno de **Pronaca** para ejecutar, previsualizar y auditar los procesos ETL del área de **Incubación** — costos, presupuestos y datos zootécnicos — sin necesidad de tocar la línea de comandos.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-6.0-092E20?logo=django&logoColor=white)
![SQL Server](https://img.shields.io/badge/SQL%20Server-ODBC-CC2927?logo=microsoftsqlserver&logoColor=white)
![License](https://img.shields.io/badge/Uso-Interno%20Pronaca-FC1F1F)

---

## ✨ ¿Qué es esto?

`etl_sip` reemplaza una colección de scripts sueltos por un **panel visual único**: cualquier usuario autorizado puede elegir un ETL, revisar una **vista previa** de los datos antes de tocar nada, ejecutarlo (o correrlo en modo *dry-run*) y ver el resultado y el histórico de corridas — todo desde el navegador.

- 🖱️ **Sin CLI necesaria** — cada ETL tiene su propio formulario, pero en caso de preferir por terminal, el panel te muestra el comando equivalente listo para copiar.
- 👁️ **Vista previa antes de ejecutar** — mirá una muestra de los datos y el conteo total antes de correr algo en producción.
- 📜 **Auditoría automática** — cada corrida (éxito, error o dry-run) queda registrada con filas extraídas/insertadas/borradas.
- 🔐 **Autenticación flexible** — usuarios locales de Django o Keycloak corporativo.

---

## 🧩 Módulos ETL disponibles

| Categoría | Proceso | Origen → Destino |
|---|---|---|
| 💰 Costos | Costo de incubación por lote | Protein → `mtech.mvProteinJournalTrans_incubacion` |
| 💰 Costos | Costo de producción en detalle | Protein → `dbo.CostoProdDetalle` |
| 💰 Costos | Presupuesto de incubadoras | Excel (`presupuesto incubadoras.xlsx`) → `dbo.ProteinJournal_Ppto` |
| 💰 Costos | Costo por lote de Incubesa | Excel (`Incubesa - costo por lote.xlsx`) → `dbo.ProteinJournal_Staging` |
| 🐣 Zootécnicos | Recepción de huevos | Mtech → `dbo.Recepcion` |
| 🐣 Zootécnicos | Cargas de incubación | Excel (`cargas.xlsx`) → `dbo.cargas` |
| 🐣 Zootécnicos | Ovoscopía | Mtech → `dbo.Ovoscopia` |

> Cada proceso soporta **modo dry-run** (extrae y cuenta, sin escribir en destino) y tamaño de lote configurable para el `INSERT`.

---

## 🛠️ Stack técnico

- **Backend:** Django 6, `mssql-django` + `pyodbc` para SQL Server, `openpyxl` para archivos Excel.
- **Frontend:** Bootstrap 5, Bootstrap Icons, CSS propio con variables de diseño, glassmorphism y animaciones (sin frameworks JS pesados — vanilla JS + `fetch`).
- **Auth:** Backend local de Django o Keycloak (`python-keycloak`), configurable por variable de entorno.
- **Base de datos:** SQL Server (origen y destino, vía ODBC Driver 17).

---

## 🚀 Empecemos!

### 1. Clonación e instalación de dependencias

```bash
git clone <url-del-repositorio>
cd etl_sip/etlsip
python -m venv venv
# Windows
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuración del `.env`

Crea `etlsip/.env` con tus credenciales reales (servidores, usuarios, tablas). Mirá [`etlsip/incubacion/README.md`](etlsip/incubacion/README.md) para el detalle completo de cada variable — incluye conexión a SQL Server origen/destino, mapeo de tablas y configuración de Keycloak.

> ⚠️ **Nunca subas tu `.env` real** — ya está en `.gitignore`.

### 3. Migración y creación de usuarios

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Ejecución el servidor

```bash
python manage.py runserver
```

Abrir el sitio con **http://localhost:8000/etl/login/** e iniciar sesión con tus crediales. 🎉

### ✅ Validación de la conexión antes de correr un ETL real

```bash
python manage.py etl_health_check
```

---

## 📁 Estructura del proyecto

```
etl_sip/
├── etlsip/
│   ├── etlsip/                 # Configuración del proyecto Django (settings, urls)
│   ├── incubacion/             # App principal: vistas, ETLs, forms, auditoría
│   │   ├── management/commands/  # Un comando por ETL (etl_incubacion, etl_cargas, ...)
│   │   ├── services.py         # Lógica de extracción/carga
│   │   ├── models.py           # ETLRunAudit (histórico de corridas)
│   │   └── README.md           # Guía operativa detallada
│   ├── reproduccion/           # App en desarrollo
│   ├── templates/incubacion/   # base.html, login.html, dashboard.html
│   └── static/incubacion/      # CSS, imágenes (logo, íconos)
├── *.xlsx                      # Plantillas de origen para ETLs basados en Excel
└── README.md                   # Este archivo
```

---

## 🎨 Interfaz

El panel usa un sistema de diseño propio inspirado en la identidad de Pronaca:

- 🔴 Paleta corporativa aplicada a botones, badges y encabezados según su función.
- 🧊 Glassmorphism en tarjetas, navbar y modales (`backdrop-filter` + transparencia).
- 🎬 Animaciones sutiles: entrada de tarjetas, sidebar que se acomoda al hacer scroll, botones con brillo interactivo al pasar el mouse.
- 📱 Responsive: el sidebar se convierte en menú off-canvas en pantallas chicas.

---

## 🔍 Flujo de uso típico

1. Elegir una ETL en el menú lateral (**Costos** o **Zootécnicos**).
2. Completar el rango de fechas / seleccionar el Excel según corresponda.
3. Click en **👁️ Vista Previa** para revisar una muestra de los datos.
4. Correr primero en **Modo de Prueba (Dry Run)** para validar conteos.
5. Ejecutár el ETL real y seguir con el progreso en vivo.
6. Revisar el resultado y el **Histórico de Corridas** a la derecha.

---

## 📚 Documentación adicional

- [`etlsip/incubacion/README.md`](etlsip/incubacion/README.md) — configuración de `.env`, health check, comportamiento de recarga completa y troubleshooting.
- [`etlsip/incubacion/KEYCLOAK.md`](etlsip/incubacion/KEYCLOAK.md) — integración con Keycloak corporativo.

---

## 🤝 Uso interno

Este proyecto es de uso interno de **Pronaca**. Para dudas o acceso, por favor contactar al equipo de Gestión Analítica & Información Técnica.
