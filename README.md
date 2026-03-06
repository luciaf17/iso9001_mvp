# ISO 9001 MVP – Documentación técnica

## 1. Objetivo del sistema
Este proyecto es una **web app interna** para micro y pequeñas empresas que permite
gestionar un Sistema de Gestión de la Calidad conforme a ISO 9001, con foco en:

- Trazabilidad
- Control documental
- Registros auditables
- Simplicidad operativa

El sistema NO es multi-tenant:  
cada empresa tiene su propia instancia y base de datos.

---

## 2. Stack técnico
- Backend: Django (monolito)
- Base de datos: PostgreSQL
- Frontend: Django Templates + HTMX
- Autenticación: Django default + Groups
- Control de configuración: `.env` + django-environ
- Versionado: Git + GitHub

---

## 3. Estructura general del proyecto

iso9001-mvp/
├─ config/ # settings, urls, wsgi
├─ apps/ # aplicaciones del sistema
│ ├─ core/ # funcionalidades transversales
│ └─ docs/ # control documental (Módulo 1)
├─ templates/ # templates globales
├─ static/ # archivos estáticos
├─ media/ # archivos subidos (no versionados en git)
├─ docs/ # documentación técnica del proyecto
├─ manage.py
└─ .env


---

## 4. App `core` (núcleo del sistema)

### Qué es
La app `core` contiene funcionalidades **transversales** utilizadas por todos los módulos.

### Para qué sirve
Evita duplicar lógica y asegura trazabilidad consistente en todo el sistema.

### Qué contiene actualmente
- `AuditEvent`: registro de auditoría (quién hizo qué y cuándo)
- Helpers de logging y servicios comunes

### Archivos clave
- `apps/core/models.py`
- `apps/core/admin.py`
- `apps/core/services.py`

---

## 5. App `docs` (Control Documental – Módulo 1)

### Qué es
Módulo encargado del **control de la información documentada** del sistema de gestión.

### Para qué sirve
- Controlar documentos ISO (manuales, procedimientos, instructivos, formatos)
- Gestionar versiones
- Asegurar que exista una única versión vigente
- Registrar aprobaciones y obsolescencias

### Funcionalidades del módulo
- Alta de documentos
- Subida de versiones (PDF / Word)
- Aprobación de versiones
- Historial completo y trazable
- Vista de documentos vigentes

### Importante
Este módulo **NO crea registros operativos**.
Solo controla documentación.

---

## 6. Trazabilidad (AuditEvent)

Toda acción relevante del sistema debe generar un `AuditEvent`, por ejemplo:
- Crear documento
- Subir nueva versión
- Aprobar documento
- Obsoletar versión

Esto permite demostrar trazabilidad ante auditoría ISO.

---

## 7. Convenciones de desarrollo
- Un ticket = un commit
- Lógica de negocio en `services.py`
- Views delgadas
- Permisos explícitos por Groups
- No hardcodear configuraciones sensibles

---

## 8. Estado actual del proyecto
- CORE-01 AuditEvent: COMPLETADO
- DOCS-01 Modelos Control Documental: COMPLETADO
- DOCS-02 Servicio de aprobación: COMPLETADO
- DOCS-04 Admin: COMPLETADO
- DOCS-04 Forms: COMPLETADO
- DOCS-05 UI básica + HTMX: COMPLETADO
- DOCS-07: Motivo del cambio en versiones: COMPLETADO

9. App core – Gestión Organizacional ISO

Además de funcionalidades transversales, la app core contiene actualmente:

Organización y estructura

Organization

Site

Process jerárquico (Proceso → Subproceso → Sector)

Mapa de procesos visual

Carga masiva inicial vía management command

Contexto de la organización (ISO 4.1 – 4.2)

OrganizationContext editable

Alcance del SGC

Historial de actualización

Auditoría automática

Partes interesadas (INT-01)

Registro de stakeholders

Necesidades y expectativas

Relación con procesos

Evidencia documental

Control de estado y revisión

Riesgos y Oportunidades (RSK-01)

Identificación por proceso o stakeholder

Probabilidad (1–5)

Impacto (1–5)

Cálculo automático de score

Nivel automático (LOW / MEDIUM / HIGH)

Plan de tratamiento

Responsable y vencimiento

Evidencia documental

Registro en AuditEvent

10. Control de permisos

Solo grupos Admin y Calidad pueden crear y editar:

Procesos

Contexto

Stakeholders

Riesgos

Documentos

Otros usuarios:

Solo lectura

11. Principios arquitectónicos

Monolito Django

Single-tenant por instancia

Lógica de negocio en servicios

Cálculos automáticos en modelo

Auditoría transversal obligatoria

UI simple, auditable y sin dependencia SPA

---

## 12. Mantenimiento y limpieza

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
