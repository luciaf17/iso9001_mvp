from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError

from apps.core.services import log_audit_event
from apps.docs.models import DocumentVersion, DocumentApproval


ALLOWED_APPROVERS = {"Admin", "Calidad"}


def user_can_approve(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=ALLOWED_APPROVERS).exists()


@transaction.atomic
def approve_document_version(*, version_id: int, user, comment: str = "") -> DocumentVersion:
    """
    Approves a DocumentVersion:
    - sets selected version to APPROVED
    - sets any other APPROVED versions of the same document to OBSOLETE
    - creates DocumentApproval (1:1)
    - logs AuditEvent
    """
    if not user_can_approve(user):
        raise PermissionDenied("No tenés permisos para aprobar documentos.")

    version = (
        DocumentVersion.objects
        .select_for_update()
        .select_related("document")
        .get(pk=version_id)
    )

    # Validar que la versión esté en un estado aprobable
    if version.status == DocumentVersion.Status.APPROVED:
        raise ValidationError("Esta versión ya está aprobada.")
    
    if version.status == DocumentVersion.Status.OBSOLETE:
        raise ValidationError("No se puede aprobar una versión obsoleta.")
    
    # Solo permitir aprobar DRAFT o IN_REVIEW
    if version.status not in (DocumentVersion.Status.DRAFT, DocumentVersion.Status.IN_REVIEW):
        raise ValidationError(f"No se puede aprobar una versión en estado {version.get_status_display()}.")

    # Obsoletar otras aprobadas del mismo documento
    (DocumentVersion.objects
        .select_for_update()
        .filter(document=version.document, status=DocumentVersion.Status.APPROVED)
        .exclude(pk=version.pk)
        .update(status=DocumentVersion.Status.OBSOLETE)
    )

    # Aprobar esta versión
    version.status = DocumentVersion.Status.APPROVED
    version.save(update_fields=["status"])

    # Crear o reemplazar aprobación (debería no existir si se usa bien)
    approval, created = DocumentApproval.objects.update_or_create(
        document_version=version,
        defaults={
            "approved_by": user,
            "approved_at": timezone.now(),
            "comment": comment or "",
        },
    )

    # Audit
    log_audit_event(
        actor=user,
        action="docs.version.approved",
        instance=version,
        metadata={
            "document_code": version.document.code,
            "version_number": version.version_number,
            "approval_created": created,
        },
    )

    return version
