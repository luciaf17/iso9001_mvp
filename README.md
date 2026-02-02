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

