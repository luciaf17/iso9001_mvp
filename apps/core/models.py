from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Organization(models.Model):
    """Empresa/organizacion bajo ISO 9001."""

    name = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Nombre",
        help_text="Nombre legal o comercial de la empresa."
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Organizacion"
        verbose_name_plural = "Organizaciones"

    def __str__(self):
        return self.name


class Site(models.Model):
    """Sede fisica o ubicacion de una organizacion."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="sites",
        verbose_name="Organizacion"
    )
    name = models.CharField(
        max_length=150,
        verbose_name="Nombre",
        help_text="Nombre de la sede o ubicacion."
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Sede"
        verbose_name_plural = "Sedes"

    def __str__(self):
        return f"{self.organization} - {self.name}"


class Process(models.Model):
    """Proceso del Sistema de Gestion de la Calidad (mapa de procesos)."""

    class ProcessType(models.TextChoices):
        STRATEGIC = "STRATEGIC", "Estrategico"
        MISSIONAL = "MISSIONAL", "Misional"
        SUPPORT = "SUPPORT", "Soporte"

    class Level(models.IntegerChoices):
        PROCESS = 1, "Proceso"
        SUBPROCESS = 2, "Subproceso"
        SECTOR = 3, "Sector"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="processes",
        verbose_name="Organizacion"
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processes",
        verbose_name="Sede"
    )
    code = models.CharField(
        max_length=30,
        verbose_name="Codigo",
        help_text="Identificador del proceso (ej: 09, 01, C1)."
    )
    name = models.CharField(
        max_length=120,
        verbose_name="Nombre"
    )
    process_type = models.CharField(
        max_length=20,
        choices=ProcessType.choices,
        verbose_name="Tipo de proceso"
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Proceso padre"
    )
    level = models.PositiveSmallIntegerField(
        choices=Level.choices,
        verbose_name="Nivel"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )

    class Meta:
        ordering = ["code"]
        verbose_name = "Proceso"
        verbose_name_plural = "Procesos"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_process_code_per_org",
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def clean(self):
        super().clean()
        if self.level not in [1, 2, 3]:
            raise ValidationError({"level": "El nivel debe ser 1, 2 o 3."})

        if self.level == 1 and self.parent is not None:
            raise ValidationError({"parent": "Un proceso de nivel 1 no puede tener padre."})

        if self.level in [2, 3] and self.parent is None:
            raise ValidationError({"parent": "Un proceso de nivel 2 o 3 debe tener padre."})

        if self.level == 2 and self.parent is not None and self.parent.level != 1:
            raise ValidationError({"parent": "El padre de un nivel 2 debe ser nivel 1."})

        if self.level == 3 and self.parent is not None and self.parent.level != 2:
            raise ValidationError({"parent": "El padre de un nivel 3 debe ser nivel 2."})

        if self.parent and self.parent.organization != self.organization:
            raise ValidationError({
                "parent": "El proceso padre debe pertenecer a la misma organizacion."
            })

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)


class Stakeholder(models.Model):
    """Parte interesada segun ISO 9001 (clausula 4.2)."""

    class StakeholderType(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Cliente"
        SUPPLIER = "SUPPLIER", "Proveedor"
        INTERNAL = "INTERNAL", "Interno"
        REGULATOR = "REGULATOR", "Regulador"
        COMMUNITY = "COMMUNITY", "Comunidad"
        OTHER = "OTHER", "Otro"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="stakeholders",
        verbose_name="Organizacion",
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stakeholders",
        verbose_name="Sede",
    )
    name = models.CharField(
        max_length=150,
        verbose_name="Nombre",
    )
    stakeholder_type = models.CharField(
        max_length=20,
        choices=StakeholderType.choices,
        verbose_name="Tipo",
    )
    expectations = models.TextField(
        verbose_name="Expectativas",
    )
    related_process = models.ForeignKey(
        Process,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stakeholders",
        verbose_name="Proceso relacionado",
    )
    related_document = models.ForeignKey(
        "docs.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stakeholders",
        verbose_name="Documento relacionado",
    )
    review_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de revision",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado el",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Actualizado el",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Parte interesada"
        verbose_name_plural = "Partes interesadas"

    def __str__(self):
        return f"{self.name} ({self.stakeholder_type})"


class RiskOpportunity(models.Model):
    """Registro de riesgos y oportunidades por proceso (ISO 9001)."""

    class Kind(models.TextChoices):
        RISK = "RISK", "Riesgo"
        OPPORTUNITY = "OPPORTUNITY", "Oportunidad"

    class Level(models.TextChoices):
        LOW = "LOW", "Bajo"
        MEDIUM = "MEDIUM", "Medio"
        HIGH = "HIGH", "Alto"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Abierto"
        IN_PROGRESS = "IN_PROGRESS", "En progreso"
        CLOSED = "CLOSED", "Cerrado"

    PROBABILITY_CHOICES = [(i, str(i)) for i in range(1, 6)]
    IMPACT_CHOICES = [(i, str(i)) for i in range(1, 6)]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="risks_opportunities",
        verbose_name="Organizacion",
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risks_opportunities",
        verbose_name="Sede",
    )
    related_process = models.ForeignKey(
        Process,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risks_opportunities",
        verbose_name="Proceso relacionado",
    )
    stakeholder = models.ForeignKey(
        "core.Stakeholder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risks_opportunities",
        verbose_name="Parte interesada",
    )
    title = models.CharField(
        max_length=200,
        verbose_name="Titulo",
    )
    description = models.TextField(
        verbose_name="Descripcion",
    )
    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        verbose_name="Tipo",
    )
    probability = models.PositiveSmallIntegerField(
        choices=PROBABILITY_CHOICES,
        verbose_name="Probabilidad",
    )
    impact = models.PositiveSmallIntegerField(
        choices=IMPACT_CHOICES,
        verbose_name="Impacto",
    )
    score = models.PositiveSmallIntegerField(
        editable=False,
        verbose_name="Puntaje",
    )
    level = models.CharField(
        max_length=10,
        choices=Level.choices,
        editable=False,
        verbose_name="Nivel",
    )
    treatment_plan = models.TextField(
        blank=True,
        verbose_name="Plan de tratamiento",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risks_opportunities",
        verbose_name="Responsable",
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha limite",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        verbose_name="Estado",
    )
    evidence_document = models.ForeignKey(
        "docs.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risks_opportunities",
        verbose_name="Documento evidencia",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado el",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Actualizado el",
    )

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Riesgo u oportunidad"
        verbose_name_plural = "Riesgos y oportunidades"

    def __str__(self):
        return f"{self.title} ({self.get_kind_display()})"

    def clean(self):
        super().clean()
        if self.probability is not None and not 1 <= self.probability <= 5:
            raise ValidationError({"probability": "La probabilidad debe estar entre 1 y 5."})
        if self.impact is not None and not 1 <= self.impact <= 5:
            raise ValidationError({"impact": "El impacto debe estar entre 1 y 5."})

    def _calculate_score_level(self):
        if self.probability is None or self.impact is None:
            return 0, self.Level.LOW

        score = self.probability * self.impact
        if score <= 7:
            level = self.Level.LOW
        elif score <= 14:
            level = self.Level.MEDIUM
        else:
            level = self.Level.HIGH
        return score, level

    def save(self, *args, **kwargs):
        self.full_clean()
        self.score, self.level = self._calculate_score_level()
        super().save(*args, **kwargs)


class AuditEvent(models.Model):
    """Modelo para trazabilidad transversal de eventos del sistema."""
    
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Actor",
        help_text="Usuario que ejecutó la acción"
    )
    action = models.CharField(
        max_length=100,
        verbose_name="Acción",
        help_text="Tipo de acción realizada"
    )
    object_type = models.CharField(
        max_length=100,
        verbose_name="Tipo de objeto",
        help_text="Tipo de objeto afectado"
    )
    object_id = models.PositiveIntegerField(
        verbose_name="ID de objeto",
        help_text="ID del objeto afectado"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha y hora"
    )
    metadata = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Metadatos",
        help_text="Información adicional en formato JSON"
    )
    
    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Evento de auditoría"
        verbose_name_plural = "Eventos de auditoría"
    
    def __str__(self):
        actor_name = self.actor.username if self.actor else "Sistema"
        return f"{actor_name} - {self.action} - {self.object_type}#{self.object_id}"


class OrganizationContext(models.Model):
    organization = models.OneToOneField(
        Organization,
        on_delete=models.PROTECT,
        related_name="context",
        verbose_name="Organizacion",
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organization_contexts",
        verbose_name="Sede",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organization_contexts",
        verbose_name="Responsable",
    )
    review_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de revision",
    )
    summary = models.TextField(
        blank=True,
        verbose_name="Resumen",
    )
    quality_policy_doc = models.ForeignKey(
        "docs.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="context_quality_policy",
        verbose_name="Politica de calidad",
    )
    process_map_doc = models.ForeignKey(
        "docs.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="context_process_map",
        verbose_name="Mapa de procesos",
    )
    org_chart_doc = models.ForeignKey(
        "docs.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="context_org_chart",
        verbose_name="Organigrama",
    )
    context_analysis_doc = models.ForeignKey(
        "docs.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="context_analysis",
        verbose_name="Analisis de contexto",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Actualizado",
    )

    class Meta:
        verbose_name = "Contexto de la organizacion"
        verbose_name_plural = "Contextos de la organizacion"

    def __str__(self):
        return f"Contexto - {self.organization}"

class NoConformity(models.Model):
    """No conformidad detectada en el sistema de gestion."""

    class Origin(models.TextChoices):
        AUDIT = "AUDIT", "Auditoria"
        CUSTOMER = "CUSTOMER", "Cliente"
        INTERNAL = "INTERNAL", "Interna"
        PRODUCTION = "PRODUCTION", "Produccion"
        OTHER = "OTHER", "Otro"

    class Severity(models.TextChoices):
        MINOR = "MINOR", "Menor"
        MAJOR = "MAJOR", "Mayor"
        CRITICAL = "CRITICAL", "Critica"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Abierta"
        ANALYSIS = "ANALYSIS", "En analisis"
        ACTION = "ACTION", "En accion"
        CLOSED = "CLOSED", "Cerrada"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="nonconformities",
        verbose_name="Organizacion",
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nonconformities",
        verbose_name="Sede",
    )
    related_process = models.ForeignKey(
        Process,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nonconformities",
        verbose_name="Proceso relacionado",
    )
    related_document = models.ForeignKey(
        "docs.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nonconformities_as_related",
        verbose_name="Documento relacionado",
    )
    title = models.CharField(
        max_length=200,
        verbose_name="Titulo",
    )
    description = models.TextField(
        verbose_name="Descripcion",
    )
    origin = models.CharField(
        max_length=20,
        choices=Origin.choices,
        verbose_name="Origen",
    )
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        verbose_name="Severidad",
    )
    detected_at = models.DateField(
        verbose_name="Fecha deteccion",
        help_text="Fecha en la que se detecto la no conformidad",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nonconformities",
        verbose_name="Responsable",
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha limite",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        verbose_name="Estado",
    )
    evidence_document = models.ForeignKey(
        "docs.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nonconformities_as_evidence",
        verbose_name="Documento evidencia",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Actualizado",
    )

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "No conformidad"
        verbose_name_plural = "No conformidades"

    def __str__(self):
        return f"NC-{self.id}: {self.title}"