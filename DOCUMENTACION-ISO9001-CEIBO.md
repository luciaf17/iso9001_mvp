# ISO 9001 QMS — Metalúrgica Ceibo S.R.L.

## Documentación Técnica Completa

**Última actualización:** Marzo 2026
**Cliente:** Metalúrgica Ceibo S.R.L. — Armstrong, Santa Fe
**Stack:** Django 5.2 · PostgreSQL · HTMX · Tailwind · DRF · ReportLab
**Deploy:** Railway (instancia por cliente)
**Bot:** Telegram + n8n + OpenAI Whisper + GPT-4o-mini

---

## 1. Descripción General

Sistema de Gestión de Calidad ISO 9001:2015 para PyMEs metalúrgicas. Cubre el 90% de las cláusulas de la norma con 25 modelos, 176+ tests, dashboard con Chart.js, y un bot de Telegram para reportar Productos No Conformes desde planta por audio o texto.

---

## 2. Estructura del Proyecto

```
iso9001_mvp-dev/
├── config/
│   ├── settings.py          # Configuración Django (env vars, DB, storage)
│   ├── urls.py               # URLs raíz
│   └── wsgi.py
├── apps/
│   ├── core/                 # App principal (NC, PNC, CAPA, auditorías, etc.)
│   │   ├── models.py         # 25 modelos (2500+ líneas)
│   │   ├── views.py          # 80+ views (3500+ líneas)
│   │   ├── forms.py          # ModelForms para NC, PNC, riesgos, etc.
│   │   ├── admin.py          # Admin con fieldsets ISO
│   │   ├── pdf_generator.py  # Generador PDF formato R-05-01
│   │   ├── services.py       # log_audit_event y helpers
│   │   ├── tests.py          # 143 tests
│   │   ├── competency_views.py # Views de empleados y capacitación
│   │   ├── management/commands/
│   │   │   ├── seed_ceibo_process_map.py   # Mapa de procesos CEIBO
│   │   │   ├── seed_audit_questions.py     # Preguntas auditoría
│   │   │   └── seed_ceibo_demo_data.py     # Data demo completa
│   │   └── templates/core/   # 50+ templates HTMX
│   ├── docs/                 # Módulo de documentos ISO
│   │   ├── models.py         # Document, DocumentVersion
│   │   ├── views.py          # CRUD + biblioteca + versiones
│   │   └── templates/docs/
│   ├── org/                  # Mapa de procesos visual
│   │   ├── views.py
│   │   └── templates/org/
│   └── api/                  # API REST para bot Telegram
│       ├── serializers.py    # NC, PNC, CAPA, Process, User
│       ├── views.py          # Endpoints CRUD
│       ├── urls.py           # /api/*
│       └── tests.py          # 9 tests API
├── static/
│   └── img/logo_ceibo.jpeg   # Logo para PDFs
├── templates/                # Base templates
├── requirements.txt
├── Procfile                  # gunicorn + migrate
├── runtime.txt
└── manage.py
```

---

## 3. Modelos (25 modelos — apps/core/models.py)

### Organización y Contexto (ISO 4.1-4.4)

| Modelo | Cláusula | Descripción |
|--------|----------|-------------|
| **Organization** | 4.1 | Empresa bajo ISO 9001 |
| **Site** | 4.1 | Sede física |
| **OrganizationContext** | 4.1 | Contexto, alcance SGC, política calidad |
| **Stakeholder** | 4.2 | Partes interesadas y expectativas |
| **Process** | 4.4 | Mapa de procesos (3 niveles: proceso/subproceso/sector) |

### Riesgos y Oportunidades (ISO 6.1)

| Modelo | Descripción |
|--------|-------------|
| **RiskOpportunity** | Riesgos/oportunidades con probabilidad×impacto (score auto-calculado) |

### No Conformidades y CAPA (ISO 8.7, 10.2)

| Modelo | Descripción |
|--------|-------------|
| **NoConformity** | NC con flujo: Abierta → En análisis → En tratamiento → Verificación → Cerrada |
| **CAPAAction** | Acciones correctivas/contencion/preventivas vinculadas a NC o hallazgo |
| **NonconformingOutput** | Producto/Servicio No Conforme (PNC) con disposición |

### Auditorías (ISO 9.2)

| Modelo | Descripción |
|--------|-------------|
| **InternalAudit** | Auditoría planificada con procesos, archivos |
| **AuditQuestion** | Preguntas reutilizables por tipo de proceso |
| **AuditAnswer** | Respuestas OK/Not OK/NA |
| **AuditFinding** | Hallazgos (área de preocupación/oportunidad de mejora/NC) |

### Objetivos e Indicadores (ISO 6.2, 9.1)

| Modelo | Descripción |
|--------|-------------|
| **QualityObjective** | Objetivos medibles con status auto-calculado |
| **QualityIndicator** | Indicadores con frecuencia y meta |
| **IndicatorMeasurement** | Mediciones periódicas |

### Revisión por Dirección (ISO 9.3)

| Modelo | Descripción |
|--------|-------------|
| **ManagementReview** | Entradas (9.3.2) y salidas (9.3.3) completas |

### Proveedores (ISO 8.4)

| Modelo | Descripción |
|--------|-------------|
| **Supplier** | Proveedor con categoría y estado de aprobación |
| **SupplierEvaluation** | Evaluación con scores calidad/entrega/precio |

### Competencias (ISO 7.2)

| Modelo | Descripción |
|--------|-------------|
| **Employee** | Empleado con puesto y departamento |
| **Competency** | Competencia requerida por puesto |
| **EmployeeCompetency** | Brecha automática (nivel actual vs requerido) |
| **Training** | Capacitación con evidencia |
| **TrainingAttendance** | Asistencia con evaluación de eficacia |

### Trazabilidad

| Modelo | Descripción |
|--------|-------------|
| **AuditEvent** | Log transversal de todas las acciones del sistema |

---

## 4. API REST (apps/api/)

Base URL: `https://iso9001mvp-production-f987.up.railway.app/api/`

Autenticación: Token (`Authorization: Token <key>`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/token/` | POST | Obtener token (username + password) |
| `/api/health/` | GET | Health check |
| `/api/processes/` | GET | Listar procesos |
| `/api/users/` | GET | Listar usuarios |
| `/api/nc/` | GET | Listar NCs (filtros: status, severity) |
| `/api/nc/create/` | POST | Crear NC |
| `/api/nc/<id>/` | GET | Detalle NC |
| `/api/pnc/` | GET | Listar PNCs (filtros: status, severity) |
| `/api/pnc/create/` | POST | Crear PNC |
| `/api/pnc/<id>/` | GET | Detalle PNC |
| `/api/capa/create/` | POST | Crear CAPA |

**Token actual (bot-dev):** `cb05506d0a793d3c19c15a72a0a39b5c5a734748`

### Ejemplo: Crear PNC

```bash
curl -X POST https://iso9001mvp-production-f987.up.railway.app/api/pnc/create/ \
  -H "Authorization: Token cb05506d0a793d3c19c15a72a0a39b5c5a734748" \
  -H "Content-Type: application/json" \
  -d '{
    "product_or_service": "Pala Frontal PF-300",
    "description": "3 unidades con soldadura porosa",
    "detected_at": "2026-03-08",
    "severity": "MAJOR",
    "source": "TELEGRAM_AUDIO"
  }'
```

---

## 5. Bot de Telegram (n8n Cloud)

### Flujo

```
Usuario manda mensaje/audio en Telegram
  → n8n Telegram Trigger
  → Switch (audio o texto?)
  → Si audio: Telegram Get File → OpenAI Whisper (transcripción)
  → Set (preparar user_text, input_type, chat_id, username)
  → Merge (une ramas texto y audio)
  → OpenAI GPT-4o-mini (extrae: product_or_service, description, severity, quantity)
  → Code (parsear JSON, agregar prefijo trazabilidad)
  → HTTP Request POST /api/pnc/create/
  → Telegram Send Message (confirmación con código PNC)
```

### Credenciales n8n

- **Telegram Bot Token:** `8518036194:AAE7Z7CXU-_-fZc8JiQ7F6Vl6osNyEHWPDU`
- **OpenAI:** tu API key
- **Header Auth (Django):** Header `Authorization` / Value `Token cb05506d0a793d3c19c15a72a0a39b5c5a734748`

### Nodos del workflow (en orden)

1. **Telegram Trigger** — On Message
2. **Switch** — voice.file_id exists → audio / text exists → texto
3. **Telegram Get File** (rama audio) — descarga audio
4. **OpenAI Whisper** (rama audio) — transcribe en español
5. **Set "Preparar Audio"** — user_text, input_type=TELEGRAM_AUDIO, chat_id, username
6. **Set "Preparar Texto"** (rama texto) — user_text, input_type=TELEGRAM_TEXT, chat_id, username
7. **Merge** — Append
8. **OpenAI GPT-4o-mini** — System prompt que extrae campos del PNC en JSON
9. **Code "Parsear respuesta"** — parsea JSON, agrega prefijo trazabilidad
10. **HTTP Request "Crear PNC"** — POST a /api/pnc/create/ con Header Auth
11. **Telegram "Éxito"** — responde con código PNC y link
12. **Telegram "Error"** (rama error del HTTP) — mensaje de error

---

## 6. Deploy en Railway

### Servicios

| Servicio | Branch | Descripción |
|----------|--------|-------------|
| **Django (producción)** | `dev` | Para que CEIBO pruebe |
| **Django (bot-dev)** | `bot-dev` | Para desarrollo del bot |
| **PostgreSQL** | — | Base de datos (auto-provisionada) |
| **Volume** | — | Montado en `/app/media` para archivos |

### Variables de entorno (Railway)

```
DJANGO_SECRET_KEY=<generada>
DJANGO_DEBUG=False
DATABASE_URL=<auto de PostgreSQL service>
CSRF_TRUSTED_ORIGINS=https://iso9001mvp-production-f987.up.railway.app
```

### Archivos de deploy

- `Procfile`: `web: gunicorn config.wsgi --bind 0.0.0.0:$PORT` + `release: python manage.py migrate`
- `runtime.txt`: versión Python
- `requirements.txt`: todas las dependencias

### URL producción

`https://iso9001mvp-production-f987.up.railway.app`

---

## 7. Usuarios del sistema

### Usuarios de demo (seed data)

| Username | Rol | Password |
|----------|-----|----------|
| jlambertucci | Admin + Calidad | ceibo2026 |
| earregui | Calidad | ceibo2026 |
| cgarcia | Operario | ceibo2026 |
| mfernandez | Operario | ceibo2026 |
| lsosa | Operario | ceibo2026 |

### Cargar datos de demo

```bash
# Con DATABASE_URL configurada (local o Railway)
python manage.py seed_ceibo_process_map
python manage.py seed_audit_questions
python manage.py seed_ceibo_demo_data
```

---

## 8. Generación de PDFs

El sistema genera PDFs con formato R-05-01 de CEIBO para NC y PNC.

- **Archivo:** `apps/core/pdf_generator.py`
- **Librería:** ReportLab (canvas directo)
- **Logo:** `static/img/logo_ceibo.jpeg`

### Layout del PDF

4 secciones con textos verticales en el costado izquierdo:
1. "A ser completado por el Responsable de Sector" — datos generales, descripción
2. "A ser completado por la Organización" — causa raíz, acción correctiva, disposición
3. "A ser completado por el Auditor" — verificación, estado, comentarios
4. "A ser completado por el Responsable de Sistemas" — clasificación, impacto

### URLs de descarga

- NC: `/nc/<pk>/pdf/` → filename `R-05-01_NC-2026-XXX.pdf`
- PNC: `/pnc/<pk>/pdf/` → filename `R-05-01-PNC_PNC-2026-XXX.pdf`

---

## 9. Cómo hacer cambios (Guía paso a paso)

### 9.1 Setup local

```bash
# Clonar
git clone <repo-url> iso9001_mvp
cd iso9001_mvp
git checkout dev

# Entorno virtual
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Variables de entorno (.env en raíz)
DJANGO_SECRET_KEY=mi-clave-secreta-local
DJANGO_DEBUG=True
DATABASE_URL=postgres://user:pass@localhost:5432/iso9001_dev

# Migrar y cargar data
python manage.py migrate
python manage.py seed_ceibo_process_map
python manage.py seed_audit_questions
python manage.py seed_ceibo_demo_data
python manage.py createsuperuser

# Correr
python manage.py runserver
```

### 9.2 Flujo de ramas

```
dev (producción CEIBO)
 └── bot-dev (desarrollo bot + features nuevos)
      └── feature/xxx (features específicos — opcional)
```

**Regla:** nunca pushear directo a `dev`. Siempre trabajar en `bot-dev` o en una rama feature, probar, y después mergear a `dev`.

### 9.3 Hacer un cambio

```bash
# 1. Asegurate de estar en bot-dev actualizada
git checkout bot-dev
git pull origin bot-dev

# 2. Hacé tus cambios (modelos, views, templates, etc.)

# 3. Si tocaste modelos:
python manage.py makemigrations core
python manage.py migrate

# 4. Correr tests
python manage.py test apps.core apps.docs apps.api --verbosity=2

# 5. Commit
git add .
git commit -m "feat: descripción del cambio"

# 6. Push a bot-dev (Railway redeploya automático)
git push origin bot-dev

# 7. Verificar en Railway que deployó bien

# 8. Cuando esté estable, mergear a dev
git checkout dev
git merge bot-dev
git push origin dev
```

### 9.4 Si algo se rompe en producción

```bash
# Volver al commit anterior en dev
git checkout dev
git log --oneline -5  # ver commits recientes
git revert HEAD        # revertir último commit
git push origin dev    # Railway redeploya
```

### 9.5 Actualizar el bot de n8n

1. Ir a n8n.cloud → tu workspace
2. Abrir workflow "Bot Telegram - ISO 9001"
3. Editar el nodo que necesites
4. Guardar → el workflow se actualiza en vivo
5. Probar mandando mensaje al bot

### 9.6 Agregar un modelo nuevo

```bash
# 1. Agregar clase en apps/core/models.py
# 2. Agregar admin en apps/core/admin.py
# 3. Crear form en apps/core/forms.py
# 4. Crear views en apps/core/views.py
# 5. Crear templates en apps/core/templates/core/
# 6. Agregar URLs en apps/core/urls.py
# 7. Migrar:
python manage.py makemigrations core
python manage.py migrate
# 8. Agregar tests
# 9. Correr tests y pushear
```

### 9.7 Agregar un endpoint a la API

```bash
# 1. Crear serializer en apps/api/serializers.py
# 2. Crear view en apps/api/views.py
# 3. Agregar URL en apps/api/urls.py
# 4. Agregar tests en apps/api/tests.py
# 5. Correr tests y pushear
```

---

## 10. Comandos útiles

```bash
# Correr servidor local
python manage.py runserver

# Correr tests
python manage.py test apps.core apps.docs apps.api -v2

# Crear superusuario
python manage.py createsuperuser

# Ver migraciones pendientes
python manage.py showmigrations

# Shell Django
python manage.py shell

# Cargar seeds en Railway (desde local con DATABASE_URL temporal)
$env:DATABASE_URL="postgresql://postgres:xxx@xxx.railway.app:5432/railway"
python manage.py seed_ceibo_process_map
python manage.py seed_audit_questions
python manage.py seed_ceibo_demo_data

# Generar token API para un usuario
python manage.py shell
>>> from rest_framework.authtoken.models import Token
>>> from django.contrib.auth.models import User
>>> Token.objects.create(user=User.objects.get(username='jlambertucci'))
```

---

## 11. Módulos del sistema (URLs)

| URL | Módulo | Cláusula ISO |
|-----|--------|-------------|
| `/dashboard/` | Dashboard principal | — |
| `/context/` | Contexto de la organización | 4.1 |
| `/stakeholders/` | Partes interesadas | 4.2 |
| `/org/` | Mapa de procesos | 4.4 |
| `/risks/` | Riesgos y oportunidades | 6.1 |
| `/objectives/` | Objetivos de calidad | 6.2 |
| `/employees/` | Empleados | 7.1 |
| `/competencies/` | Competencias | 7.2 |
| `/trainings/` | Capacitaciones | 7.2 |
| `/docs/` | Documentos y versiones | 7.5 |
| `/nc/` | No Conformidades | 10.2 |
| `/pnc/` | Productos No Conformes | 8.7 |
| `/suppliers/` | Proveedores | 8.4 |
| `/audits/` | Auditorías internas | 9.2 |
| `/indicators/` | Indicadores de calidad | 9.1 |
| `/management-reviews/` | Revisión por dirección | 9.3 |
| `/admin/` | Admin Django | — |

---

## 12. Dependencias (requirements.txt)

| Paquete | Versión | Uso |
|---------|---------|-----|
| Django | 5.2.11 | Framework principal |
| djangorestframework | 3.15.2 | API REST |
| django-environ | 0.12.0 | Variables de entorno |
| django-filter | 25.2 | Filtros en listas |
| django-cors-headers | 4.9.0 | CORS para API |
| psycopg | 3.3.2 | Driver PostgreSQL |
| whitenoise | 6.11.0 | Archivos estáticos en producción |
| gunicorn | 22.0.0 | Servidor WSGI producción |
| dj-database-url | 2.3.0 | Parsear DATABASE_URL |
| reportlab | 4.2.5 | Generación de PDFs |

---

## 13. Roadmap (pendientes)

### En progreso
- [ ] Ajustes cosméticos del PDF (headers grises, líneas sección 4)
- [ ] Bot para NC (similar al de PNC, agregando otro flujo en n8n)

### Próximos
- [ ] Notificaciones (email/Telegram para CAPAs vencidas, NCs pendientes)
- [ ] IA: causa raíz asistida con GPT
- [ ] IA: resumen ejecutivo para revisión por dirección
- [ ] IA: detección de patrones en NCs
- [ ] Organigrama visual generado desde datos

### Futuro
- [ ] Más registros PDF (actas auditoría, evaluaciones proveedor)
- [ ] S3/Cloudinary si se necesita backup de archivos
- [ ] Multi-tenant (cuando haya 10+ clientes)

---

## 14. Contactos y accesos

| Recurso | URL / Dato |
|---------|-----------|
| App producción | https://iso9001mvp-production-f987.up.railway.app |
| Railway dashboard | https://railway.app |
| n8n cloud | https://app.n8n.cloud |
| Telegram bot | @tu_bot (buscar en Telegram) |
| Bot token | 8518036194:AAE7Z7CXU-_-fZc8JiQ7F6Vl6osNyEHWPDU |
| API token | cb05506d0a793d3c19c15a72a0a39b5c5a734748 |
