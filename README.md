# ISO 9001 MVP – Sistema de Gestión de Calidad

Aplicación web interna para micro y pequeñas empresas para gestionar un Sistema de Gestión de la Calidad (SGC) conforme a **ISO 9001:2015**.

## 📋 Descripción general

Este MVPprovee un sistema robusto, auditable y centrado en trazabilidad para:

- ✅ **Control documental** (Documentos, versiones, aprobaciones)
- ✅ **Gestión de procesos** (Mapa de procesos, responsables)
- ✅ **Análisis de contexto** (Partes interesadas, alcance del SGC)
- ✅ **Gestión de riesgos** (Identificación, scoring, tratamiento)
- ✅ **Auditorías internas** (Planificación, ejecución, hallazgos)
- ✅ **No conformidades y CAPA** (Registro, seguimiento, efectividad)
- ✅ **Objetivos de calidad** (Planificación, medición, seguimiento)
- ✅ **Indicadores de desempeño** (Mediciones periódicas)
- ✅ **Gestión de competencias** (Empleados, capacitación, brechas)
- ✅ **Evaluación de proveedores** (Registro, auditoría, mejora)
- ✅ **Revisión de gestión** (Reuniones, decisiones, evidencia)

**El sistema NO es multi-tenant:** cada empresa tiene su propia instancia y base de datos.

---

## 🛠️ Stack técnico

| Componente | Tecnología |
|-----------|-----------|
| Backend | Django 5.2.11 |
| Base de datos | PostgreSQL |
| Frontend | Django Templates + HTMX + Tailwind CSS |
| Autenticación | Django Groups (Auth, Admin, Calidad) |
| Configuración | `.env` + django-environ |
| Control de versión | Git + GitHub |
| Testing | Django TestCase |

---

## 📁 Estructura del proyecto

```
iso9001-mvp/
├─ config/                    # Configuración Django (settings, urls, wsgi)
├─ apps/
│  ├─ core/                   # Módulo transversal + organización
│  │  ├─ models.py           # Todos los modelos del sistema
│  │  ├─ services.py         # Lógica de negocio (auditoría, etc)
│  │  ├─ views.py            # Vistas de contexto y organización
│  │  ├─ competency_views.py # Vistas de competencias y capacitación
│  │  ├─ forms.py            # Formularios
│  │  ├─ urls.py             # Rutas
│  │  ├─ tests.py            # Suite de pruebas
│  │  └─ templates/          # Templates del módulo
│  ├─ docs/                   # Control documental
│  │  ├─ models.py           # Document, DocumentVersion, DocumentApproval
│  │  ├─ services.py         # Aprobación de versiones
│  │  ├─ views.py
│  │  └─ templates/
│  └─ org/                    # Gestión organizacional
│     ├─ models.py           # Mapa de procesos
│     └─ views.py
├─ templates/                # Base templates (base.html, dashboard, etc)
├─ static/css/               # CSS del sistema
├─ media/                    # Archivos subidos (documentos, evidencias)
├─ manage.py
├─ README.md
└─ .env                      # Variables de entorno (no en repo)
```

---

## 🎯 Módulos implementados

### 1. **CORE** – Auditoría y Organización

#### AuditEvent (Trazabilidad)
- **Propósito:** Registrar **quién**, **qué**, **cuándo** en cada acción relevante
- **Alcance:** Transversal a todo el sistema
- **Datos capturados:**
  - Usuario (actor)
  - Acción (event_type)
  - Objeto afectado (referencia a modelo)
  - Metadatos adicionales
  - Timestamp automático

**Flujo:** Toda vista importante (crear, editar, aprobar) registra un `AuditEvent` mediante `log_audit_event()` en `services.py`.

---

#### Organization (Empresa)
- Nombre y estado activo
- Una por instancia (single-tenant)
- Referencia principal de todos los datos

**Modelos relacionados:**
- `Site`: Ubicaciones/plantas de la organización
- `OrganizationContext`: Análisis de contexto (ISO 4.1, 4.2, 4.3)

---

#### OrganizationContext (ISO 4.1–4.3)
- **qms_scope**: Alcance del Sistema de Gestión (SCOPE-01)
- **summary**: Resumen del contexto
- **quality_policy_doc**: Documento de política de calidad
- **process_map_doc**: Mapa de procesos
- **org_chart_doc**: Organigrama
- **context_analysis_doc**: Análisis de contexto

**Auditoría:** Toda actualización de scope registra evento `core.context.scope_updated`.

---

#### Process (Procesos)
- Jerarquía: Proceso → Subproceso → Sector
- Código único (ej: P-001)
- Responsable asignado
- Linkedeo con documentos procedentes

**Uso:** Análisis de riesgos, definición de objetivos, auditórías internas.

---

#### Stakeholder (Partes Interesadas)
- Nombre y tipo (cliente, proveedor, empleado, etc)
- Necesidades y expectativas
- Relación con procesos
- Evidencia documental

**Relevancia ISO:** Cláusula 4.2 – Partes interesadas y sus necesidades.

---

#### RiskOpportunity (Riesgos y Oportunidades)
- **Matriz de probabilidad × impacto** (1–5)
- Scoring automático
- Nivel automático (LOW, MEDIUM, HIGH)
- Plan de tratamiento
- Responsable y vencimiento

**Características:**
- Puede estar vinculado a Proceso o Stakeholder
- Genera AuditEvent al crearse
- Trazabilidad completa de cambios

---

### 2. **DOCS** – Control Documental (ISO 4.4.6)

#### Document
- Código único
- Título y descripción
- Tipo (Manual, Procedimiento, Instructivo, Formato, etc)
- Estado (DRAFT, APPROVED, OBSOLETE)

#### DocumentVersion
- Archivo (PDF, Word, etc)
- Número de versión
- Estado (DRAFT, APPROVED, OBSOLETE)
- Fecha de creación

**Regla de negocio:** Solo.UNA versión puede estar APPROVED por documento.

#### DocumentApproval (OneToOne con DocumentVersion)
- Aprobador
- Fecha de aprobación
- Motivo del cambio

**Flujo de aprobación:**
1. Subir nueva versión en estado DRAFT
2. Ejecutar aprobación automática:
   - Versión anterior (si existe) → OBSOLETE
   - Nueva versión → APPROVED
   - Crear DocumentApproval
   - Registrar AuditEvent `docs.document.version_approved`

---

### 3. **ORG** – Mapa de Procesos

- Visualización de procesos jerárquicos
- Asignación de responsables
- Datos internos, no criticidad para ISO pero útil para gestión

---

### 4. **COMPETENCIAS Y CAPACITACIÓN** (ISO 7.2)

#### COMP-01: Módulo de Competencias

**Modelos:**

**Employee** (Empleado)
- Nombre, posición, departamento
- Email, estado activo
- Organización

**Competency** (Competencia)
- Nombre
- Descripción
- Puesto requerido (ej: "Operario de producción")
- Organización

**EmployeeCompetency** (Asignación)
- Relación empleado ↔ competencia
- Nivel requerido (1–5)
- Nivel actual (1–5)
- Última evaluación (fecha)
- **Brecha calculada automáticamente** (`is_gap = nivel_actual < nivel_requerido`)

**Training** (Capacitación)
- Título, descripción
- Proveedor
- Fecha de realización
- Fecha de expiración (opcional)
- Archivo de evidencia (PDF, certificado, etc)

**TrainingAttendance** (Asistencia)
- Empleado + Capacitación
- Estado (Completada / No completada)
- Efectividad evaluada (Sí/No)
- Resultado de efectividad (Efectiva / No efectiva / Parcial)
- Fecha de evaluación
- Notas

**Casos de uso:**
- Crear competencia necesaria para puesto
- Asignar competencia a empleado con brechas
- Registrar capacitación para cerrar brecha
- Registrar asistencia y efectividad
- Visualizar brechas en dashboard

---

#### COMP-02: Asignación de Competencias (HTMX Modal)

**Flujo:**

1. **Menú → Empleados** → Seleccionar empleado
2. **Botón "+ Asignar competencia"** (si tienes permisos)
3. **Modal HTMX** (`hx-get="/employees/<id>/add-competency/"`)
4. **Formulario:**
   - Competencia (excluye las ya asignadas)
   - Nivel requerido
   - Nivel actual
   - Última evaluación (fecha)
5. **Guardar:**
   - Crea `EmployeeCompetency`
   - Calcula brecha automáticamente
   - Registra AuditEvent `core.employee.competency_assigned`
   - Actualiza tabla en tiempo real (HTMX)
6. **Validación:**
   - Formulario inválido → Retorna 422 + reinyecta modal

**Características técnicas:**
- Modal con fondo oscuro y cierre por clic
- Form con campos datepicker
- Exclusión automática de competencias ya asignadas
- Manejo de errores HTMX con `HX-Retarget`

---

### 5. **AUDITORÍAS INTERNAS** (ISO 9.2)

#### InternalAudit
- Código y descripción
- Tipo (Interna / Auditando a otros)
- Período de auditoría
- Equipo auditor
- Matriz de procesos auditados

#### AuditQuestion (Preguntas)
- Texto de la pregunta
- Proceso auditado
- Referencias normativas (ISO)
- Evidencia requerida

#### AuditAnswer (Respuesta)
- Respuesta al hallazgo
- Evidencia adjunta
- Conformidad (SÍ / NO / PARCIAL)

#### AuditFinding (Hallazgos)
- Descripción del hallazgo
- Tipo (No conformidad / Oportunidad de mejora)
- Severidad (Crítica / Mayor / Menor)
- Referencia a NC si aplica

---

### 6. **NO CONFORMIDADES Y CAPA** (ISO 8.5, 10.3)

#### NoConformity (NC)
- Código autoincrementado
- Descripción, fuente (Auditoría, Cliente, Proceso, etc)
- Severidad (Crítica, Mayor, Menor)
- Estado (Abierta, Cerrada)
- Responsable y vencimiento
- Causa raíz (verificación de raíz)

#### CAPAAction (Acciones correctivas/preventivas)
- Descripción de acción
- NC o Finding relacionada
- Responsable y vencimiento
- Efectividad evaluada (fecha y resultado)
- Plan de verificación

**Flujo:**
1. Registrar NC (auditoría, cliente, etc)
2. Asignar causa raíz
3. Crear acciones CAPA
4. Ejecutar y registrar efectividad
5. Cerrar NC con evidencia

---

### 7. **OBJETIVOS DE CALIDAD Y MEDICIÓN** (ISO 6.2)

#### QualityObjective
- Objetivo (ej: "Reducir defectos a <1% en 2024")
- Proceso relacionado
- Responsable
- Frecuencia de medición
- Meta cuantificable

#### QualityIndicator + IndicatorMeasurement
- Indicador (métrica, fórmula)
- Mediciones periódicas
- Tendencia gráfica (dashboard)

**Dashboard:** Visualiza cumplimiento vs targets en tiempo real.

---

### 8. **REVISIÓN DE GESTIÓN** (ISO 5.3)

#### ManagementReview
- Fecha de realización
- Asistentes
- Resumen de desempeño (indicadores, NC, CAPA)
- Decisiones tomadas
- Archivo de actas

---

### 9. **SALIDAS NO CONFORMES** (ISO 8.6)

#### NonconformingOutput
- Descripción del producto/servicio no conforme
- Proceso responsable
- Acción tomada (retrabajar, deshecho, etc)
- Validación de disposición
- Comunicación clara a cliente

---

### 10. **EVALUACIÓN DE PROVEEDORES** (ISO 8.4)

#### Supplier
- Nombre, categoría (Materia prima, Servicios, etc)
- Contacto principal
- Contrato/acuerdo
- Archivos de evaluación

#### SupplierEvaluation
- Criterios (Precio, Calidad, Entrega, etc)
- Puntajes (1–5)
- Resultado (Aprobado / Condicional / Rechazado)
- Plan de mejora (si aplica)

---

## 📊 Flujos principales

### Flujo 1: Gestión de documentos

```
1. CREAR DOCUMENTO
   ↓ (Auditoría: docs.document.created)
2. SUBIR VERSIÓN
   ↓ (Auditoría: docs.version.uploaded)
3. APROBAR VERSIÓN
   ├─ Versión anterior (si existe) → OBSOLETE
   ├─ Nueva versión → APPROVED
   ├─ Crear DocumentApproval
   ↓ (Auditoría: docs.version.approved)
4. DOCUMENTO VIGENTE EN SISTEMA
```

---

### Flujo 2: Análisis de contexto y riesgos

```
1. DEFINIR STAKEHOLDERS (ISO 4.2)
   ↓ (Auditoría: core.stakeholder.created)
2. IDENTIFICAR RIESGOS
   ├─ Por stakeholder
   ├─ Por proceso
   ↓ (Auditoría: core.risk.created)
3. EVALUAR (Probabilidad × Impacto)
   ↓ Scoring automático → Nivel (LOW/MEDIUM/HIGH)
4. PLANENAR TRATAMIENTO
   ├─ Responsable
   ├─ Vencimiento
   ↓ (Auditoría: core.risk.updated)
5. EJECUTAR Y VERIFICAR
```

---

### Flujo 3: Competencias y capacitación

```
1. CREAR COMPETENCIA (ISO 7.2)
   ├─ Nombre, descripción
   ├─ Puesto requerido
   ↓ (Auditoría: core.competency.created)
   
2. ASIGNAR A EMPLEADO (COMP-02)
   ├─ Nivel requerido
   ├─ Nivel actual
   ├─ Última evaluación
   ↓ Brecha calculada automáticamente
   ↓ (Auditoría: core.employee.competency_assigned)
   
3. IDENTIFICAR BRECHAS
   ├─ Dashboard muestra competencias con gap
   ├─ Empleados sin formación completa
   
4. CREAR CAPACITACIÓN
   ├─ Título, proveedor
   ├─ Fecha, archivo evidencia
   ↓ (Auditoría: core.training.created)
   
5. REGISTRAR ASISTENCIA
   ├─ Empleado + Capacitación
   ├─ Efectividad evaluada
   ↓ (Auditoría: core.training.completed)
   
6. VERIFICAR CIERRE DE BRECHA
   ├─ Actualizar nivel actual en EmployeeCompetency
   ├─ Sistema recalcula brecha
```

---

### Flujo 4: Auditoría interna

```
1. PLANIFICAR AUDITORÍA (ISO 9.2)
   ├─ Definir alcance, equipo, procesos
   ↓
2. PREPARAR CUESTIONARIO
   ├─ Preguntas por proceso
   ├─ Evidencia requerida
   ↓
3. EJECUTAR AUDITORÍA
   ├─ Responder preguntas
   ├─ Registrar hallazgos
   ↓ (Auditoría: core.audit.finding_registered)
   
4. CLASIFICAR HALLAZGOS
   ├─ No conformidad → Crear NC
   ├─ Oportunidad mejora → Registrar
   ↓
5. CREAR ACCIONES CAPA
   ├─ Vinculadas a NC/Hallazgo
   ├─ Responsable, vencimiento
   ↓
6. SEGUIMIENTO
   ├─ Efectividad de acciones
   ├─ Verificación de cierre
```

---

### Flujo 5: No conformidades y CAPA

```
1. REGISTRAR NC
   ├─ Fuente (Auditoría, Cliente, Proceso, etc)
   ├─ Descripción, severidad
   ↓ (Auditoría: core.nc.created)
   
2. ASIGNAR CAUSA RAÍZ
   ├─ Investigación inicial
   ↓ (Auditoría: core.nc.analysis)
   
3. CREAR ACCIONES CORRECTIVAS
   ├─ CAPA 1: Acción inmediata
   ├─ CAPA 2: Acciones correctivas/preventivas
   ↓
4. EJECUTAR ACCIONES
   ├─ Responsable realiza acción
   ↓
5. VERIFICAR EFECTIVIDAD
   ├─ Evaluación de cierre
   ├─ Evidencia
   ↓ (Auditoría: core.capa.effectiveness_evaluated)
   
6. CERRAR NC
   ├─ Con evidencia documentada
   ↓
7. REGISTRO HISTÓRICO
   ├─ Trazabilidad completa
```

---

## 🔐 Permisos y control de acceso

### Grupos de usuarios

| Grupo | Permisos |
|-------|----------|
| **Admin** | Crear/editar TODO (documentos, procesos, usuarios, etc) |
| **Calidad** | Crear/editar módulos ISO (riesgos, auditorías, NC, CAPA, etc) |
| **Usuario** | Solo lectura |
| **Superuser** | Acceso total (Django admin) |

### Chequeo de permisos

**Función clave:** `can_edit_competency_training(user)` en `apps/core/utils.py`

```python
def can_edit_competency_training(user):
    return user.is_superuser or user.groups.filter(
        name__in=["Admin", "Calidad"]
    ).exists()
```

Aplicable a:
- Crear/editar empleados
- Crear/editar competencias
- Asignar competencias
- Registrar capacitación y asistencia

---

## 🚀 Cómo usar el sistema

### Primer login

1. Se crea automáticamente organización activa
2. Usuario admin debe crearse manualmente o con management command
3. Asignar a grupos (Admin, Calidad) según rol

### Pasos iniciales (ISO 4.1–4.3)

1. **Menú → Contexto** → Editar alcance del SGC
2. **Menú → Procesos** → Crear procesos necesarios
3. **Menú → Partes Interesadas** → Registrar stakeholders
4. **Menú → Riesgos** → Identificar y evaluar riesgos

### Para competencias

1. **Menú → Competencias** → + Nueva Competencia
2. **Menú → Empleados** → Crear empleados o ver existentes
3. **Detalle de empleado** → + Asignar competencia
4. **Menú → Capacitaciones** → + Nueva Capacitación
5. **Crear Capacitación** → Registrar asistencia
6. **Empleado → Detalle** → Ver brecha actualizada

### Para documentos

1. **Menú → Documentos** → + Nuevo Documento
2. **Documento** → + Subir Versión (PDF/Word)
3. **Versión** → Aprobar (v1.0 → v2.0 automático)
4. Versión anterior pasa a OBSOLETE automáticamente

### Para auditorías

1. **Menú → Auditorías** → + Plan de auditoría
2. **Plan** → + Preguntas por proceso
3. **Auditoría** → Ejecutar y responder
4. **Hallazgos** → Crear NC si aplica
5. **NC** → Crear acciones CAPA
6. **CAPA** → Verificar efectividad y cerrar

---

## 🧪 Testing

Todos los módulos tienen cobertura en `apps/core/tests.py`:

- CompetencyTrainingTests (9 tests)
- ContextScopeTests (4 tests)
- + Tests para Dashboard, Procesos, Riesgos, etc.

**Ejecutar tests:**

```bash
python manage.py test apps.core.tests
```

**Tests específicos:**

```bash
python manage.py test apps.core.tests.CompetencyTrainingTests
```

---

## 💾 Deployment y configuración

### Variables de entorno (.env)

```env
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=postgresql://user:password@localhost/iso9001_mvp
```

### Migraciones

```bash
python manage.py makemigrations
python manage.py migrate
```

### Creación de superuser

```bash
python manage.py createsuperuser
```

---

## 📝 Estándares de desarrollo

### Lógica de negocio
- En `services.py`
- Accesibles desde views o admin

### Views
- Lo más delgadas posible
- Permiso checks explícitos
- Inyectar AuditEvent

### Models
- Validaciones y cálculos automáticos
- Métodos de negocio (`calculate_gap()`, `approve_version()`, etc)
- Constraints en BD

### Templates
- Django Templates + HTMX
- Tailwind CSS utility classes
- Dark mode support (`dark:*`)
- NO `@apply`, NO inline styles

### Git
- Un ticket = un commit
- Mensaje: `TICKET-XX: Descripción breve`
- Ejemplo: `COMP-02: Add HTMX modal for competency assignment`

---

## 📚 Referencias

- [ISO 9001:2015](https://www.iso.org/standard/62085.html)
- [Django Docs](https://docs.djangoproject.com/)
- [HTMX](https://htmx.org/)
- [Tailwind CSS](https://tailwindcss.com/)

### Limpieza de archivos cacheados

Si es necesario eliminar archivos `__pycache__/` del control de versiones:

```bash
git rm -r --cached **/__pycache__
git commit -m "Remove pycache from tracking"
```

Los archivos `.pyc` y `__pycache__/` ya están en `.gitignore` para evitar commits futuros.

---

## 13. Estándar de templates (UI MVP)

Para mantener consistencia visual y auditabilidad en el frontend (Django Templates + HTMX):

- No usar `@apply` dentro de templates HTML.
- No usar `style="..."` inline en templates.
- Definir clases reutilizables en bloques `<style>` solo cuando sea estrictamente necesario.
- Toda tarjeta, tabla y formulario debe tener variantes de tema claro/oscuro (`dark:*`).
- Mantener vistas delgadas: evitar lógica de negocio en templates.
- Para filas clickeables, usar patrón seguro con `data-href`.

Checklist rápido antes de mergear cambios de UI:

1. `python manage.py check`
2. Abrir vistas críticas en claro y oscuro (dashboard, listas, formularios).
3. Verificar que no aparezcan fondos blancos inesperados en modo oscuro.
4. Confirmar que no se introdujeron estilos inline ni `@apply`.

Checklist visual final (modo oscuro):

- Listas: stakeholders, objetivos, indicadores, riesgos, preguntas de auditoría, NC, PNC, suppliers.
	- Verificar botones primarios/secundarios consistentes y legibles.
	- Verificar hover de filas/acciones sin fondos blancos.
	- Verificar headers de tabla con contraste correcto.
- Formularios: parte interesada, pregunta de auditoría, auditoría, checklist, acción CAPA, NC, indicador, objetivo, medición, evaluación de proveedor.
	- Verificar fondo del contenedor y de inputs (sin panel blanco).
	- Verificar labels y help text legibles en oscuro.
- Detalles: NC, objetivo, review, supplier.
	- Verificar badges, bloques de texto y alertas con contraste correcto.
	- Verificar títulos/secciones no se mezclen con el fondo.
