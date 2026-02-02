# Copilot Instructions — ISO 9001 MVP

## Project overview
This is a Django monolith for an ISO 9001 Quality Management System (QMS) MVP.
The system is internal, audit-focused, and optimized for micro/small companies.

Key principles:
- Auditability > aesthetics
- Explicit business rules
- Modular design (one module at a time)
- No multi-tenant architecture (one instance per company)

---

## Architecture
- Backend: Django (monolith)
- Database: PostgreSQL
- Frontend: Django Templates + HTMX (NO React)
- Auth: Django default + Groups
- Configuration: django-environ (.env)
- File storage: local MEDIA (no S3 yet)

Apps:
- core: transversal logic shared by all modules
- docs: Control Documental (Module 1)

---

## Core rules
### AuditEvent
- All relevant actions MUST create an AuditEvent.
- AuditEvent is transversal and must NOT contain business logic.
- Use a helper/service to create audit events (never inline in views).

---

## Control Documental (apps.docs)
### Models
- Document
- DocumentVersion
- DocumentApproval (OneToOne with DocumentVersion)

### Critical business rules
- For each Document, ONLY ONE DocumentVersion can have status=APPROVED.
- When approving a version:
  - Previous APPROVED versions MUST become OBSOLETE
  - A DocumentApproval MUST be created
  - An AuditEvent MUST be logged
- This logic MUST live in services.py and be wrapped in transaction.atomic().

### What NOT to do
- Do NOT implement business logic in models.
- Do NOT duplicate approval logic in views or templates.
- Do NOT bypass services when changing states.

---

## Development workflow
- Branches:
  - main: stable, production-ready
  - dev: active development
- One ticket = one commit
- Close one module before starting another
- Migrations are never edited after being merged

---

## Testing strategy
- Focus on critical rules, not UI.
- Test approval logic, permissions, and invariants.
- Tests must protect ISO-critical behavior.

---

## Style and conventions
- Services contain business logic
- Views are thin
- Explicit permissions checks
- Clear naming over clever code