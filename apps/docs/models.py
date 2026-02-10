from django.db import models
from django.conf import settings


class Document(models.Model):
    """Documento del Sistema de Gestión de la Calidad."""
    
    class DocType(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        PROCEDURE = "PROCEDURE", "Procedimiento"
        INSTRUCTION = "INSTRUCTION", "Instructivo"
        FORMAT = "FORMAT", "Formato"
        EXTERNAL = "EXTERNAL", "Externo"
    
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Código",
        help_text="Identificador único del documento (ej: DOC-001)"
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Título"
    )
    doc_type = models.CharField(
        max_length=20,
        choices=DocType.choices,
        verbose_name="Tipo de documento"
    )
    processes = models.ManyToManyField(
        "core.Process",
        related_name="documents",
        blank=True,
        verbose_name="Procesos",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_documents",
        verbose_name="Propietario"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado el"
    )
    
    class Meta:
        ordering = ["code"]
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
    
    def __str__(self):
        return f"[{self.code}] {self.title}"


class DocumentVersion(models.Model):
    """Versión de un documento."""
    
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Borrador"
        IN_REVIEW = "IN_REVIEW", "En revisión"
        APPROVED = "APPROVED", "Aprobado"
        OBSOLETE = "OBSOLETE", "Obsoleto"
    
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="versions",
        verbose_name="Documento"
    )
    version_number = models.CharField(
        max_length=20,
        verbose_name="Número de versión",
        help_text="Ej: 1.0, 2.1, etc."
    )
    file = models.FileField(
        upload_to="documents/",
        verbose_name="Archivo"
    )
    effective_date = models.DateField(
        verbose_name="Fecha de vigencia"
    )
    review_due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de revisión próxima"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Estado"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_versions",
        verbose_name="Creado por"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado el"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notas"
    )
    
    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "version_number"],
                name="uniq_doc_version_number"
            )
        ]
        verbose_name = "Versión de documento"
        verbose_name_plural = "Versiones de documentos"
    
    def __str__(self):
        return f"{self.document.code} v{self.version_number} ({self.status})"


class DocumentApproval(models.Model):
    """Registro de aprobación de una versión de documento."""
    
    document_version = models.OneToOneField(
        DocumentVersion,
        on_delete=models.CASCADE,
        related_name="approval",
        verbose_name="Versión de documento"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_versions",
        verbose_name="Aprobado por"
    )
    approved_at = models.DateTimeField(
        verbose_name="Aprobado el"
    )
    comment = models.TextField(
        blank=True,
        verbose_name="Comentario"
    )
    
    class Meta:
        verbose_name = "Aprobación de documento"
        verbose_name_plural = "Aprobaciones de documentos"
    
    def __str__(self):
        return f"Aprobación: {self.document_version.document.code} v{self.document_version.version_number}"
