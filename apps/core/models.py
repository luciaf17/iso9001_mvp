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
        INTERNAL_AUDIT = "INTERNAL_AUDIT", "Auditoria interna"
        EXTERNAL_AUDIT = "EXTERNAL_AUDIT", "Auditoria externa"
        CUSTOMER = "CUSTOMER", "Cliente"
        INTERNAL = "INTERNAL", "Interna"
        PRODUCTION = "PRODUCTION", "Produccion"
        SUPPLIER = "SUPPLIER", "Proveedor"
        OTHER = "OTHER", "Otro"

    class Severity(models.TextChoices):
        MINOR = "MINOR", "Menor"
        MAJOR = "MAJOR", "Mayor"
        CRITICAL = "CRITICAL", "Critica"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Abierta"
        IN_ANALYSIS = "IN_ANALYSIS", "En analisis"
        IN_TREATMENT = "IN_TREATMENT", "En tratamiento"
        VERIFICATION = "VERIFICATION", "En verificacion"
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
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Codigo",
        help_text="NC-2025-001, NC-2025-002, etc.",
        editable=False,
    )
    title = models.CharField(
        max_length=200,
        verbose_name="Titulo",
    )
    description = models.TextField(
        verbose_name="Descripcion",
    )
    origin = models.CharField(
        max_length=30,
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
    detected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="detected_nonconformities",
        verbose_name="Detectado por",
        help_text="Usuario que detecto la no conformidad",
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
    root_cause_analysis = models.TextField(
        blank=True,
        verbose_name="Analisis de causa raiz",
        help_text="Por que ocurrio la NC? Usar 5 Por ques, Ishikawa, etc.",
    )
    corrective_action = models.TextField(
        blank=True,
        verbose_name="Accion correctiva",
        help_text="Que se hara para evitar que vuelva a ocurrir?",
    )
    verification_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de verificacion",
        help_text="Fecha en la que se verifico la eficacia de la accion",
    )
    is_effective = models.BooleanField(
        default=False,
        verbose_name="Accion efectiva?",
        help_text="La accion correctiva funciono?",
    )
    verification_notes = models.TextField(
        blank=True,
        verbose_name="Notas de verificacion",
    )
    evidence_document = models.ForeignKey(
        "docs.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nonconformities_as_evidence",
        verbose_name="Documento evidencia",
    )
    closed_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de cierre",
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_nonconformities",
        verbose_name="Cerrada por",
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
        code = self.code or f"NC-{self.id}"
        return f"{code}: {self.title}"

    def clean(self):
        super().clean()

        if self.status == self.Status.VERIFICATION and not self.verification_date:
            raise ValidationError({
                "verification_date": (
                    "Debe especificar fecha de verificacion cuando el estado es "
                    "En verificacion."
                )
            })

        if self.status == self.Status.CLOSED and not self.corrective_action:
            raise ValidationError({
                "corrective_action": (
                    "Debe especificar accion correctiva antes de cerrar la NC."
                )
            })

        if self.status == self.Status.CLOSED and not self.root_cause_analysis:
            raise ValidationError({
                "root_cause_analysis": (
                    "Debe realizar analisis de causa raiz antes de cerrar la NC."
                )
            })

    def save(self, *args, **kwargs):
        from django.utils import timezone

        if not self.code:
            year = timezone.now().year
            last_nc = NoConformity.objects.filter(
                organization=self.organization,
                code__startswith=f"NC-{year}",
            ).order_by("-code").first()

            if last_nc and last_nc.code:
                try:
                    last_num = int(last_nc.code.split("-")[-1])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1

            self.code = f"NC-{year}-{new_num:03d}"

        if self.status == self.Status.CLOSED and not self.closed_date:
            self.closed_date = timezone.now().date()

        super().save(*args, **kwargs)


class CAPAAction(models.Model):
    """Accion CAPA (Corrective and Preventive Action) vinculada a una NC.

    Representa tareas especificas de ejecucion para resolver una NC.
    La NC contiene el analisis y la decision; CAPA gestiona la ejecucion.
    """

    class ActionType(models.TextChoices):
        CORRECTIVE = "CORRECTIVE", "Correctiva"
        CONTAINMENT = "CONTAINMENT", "Contencion"
        PREVENTIVE = "PREVENTIVE", "Preventiva"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Abierta"
        IN_PROGRESS = "IN_PROGRESS", "En progreso"
        DONE = "DONE", "Completada"

    no_conformity = models.ForeignKey(
        NoConformity,
        on_delete=models.CASCADE,
        related_name="capa_actions",
        verbose_name="No conformidad",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="capa_actions",
        verbose_name="Organizacion",
    )

    title = models.CharField(
        max_length=200,
        verbose_name="Titulo",
        help_text="Descripcion breve de la accion",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Descripcion detallada",
    )
    action_type = models.CharField(
        max_length=20,
        choices=ActionType.choices,
        default=ActionType.CORRECTIVE,
        verbose_name="Tipo de accion",
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="capa_actions",
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
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Completada el",
    )
    completion_notes = models.TextField(
        blank=True,
        verbose_name="Notas de completitud",
        help_text="Detalles sobre como se completo la accion",
    )

    evidence_document = models.ForeignKey(
        "docs.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="capa_actions_as_evidence",
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
        ordering = ["due_date", "created_at"]
        verbose_name = "Accion CAPA"
        verbose_name_plural = "Acciones CAPA"

    def __str__(self):
        nc_code = self.no_conformity.code if self.no_conformity_id else "-"
        return f"{self.get_action_type_display()}: {self.title} (NC: {nc_code})"

    def save(self, *args, **kwargs):
        from django.utils import timezone

        if not self.organization_id and self.no_conformity_id:
            self.organization = self.no_conformity.organization

        if self.status == self.Status.DONE and not self.completed_at:
            self.completed_at = timezone.now()

        if self.status in [self.Status.OPEN, self.Status.IN_PROGRESS] and self.completed_at:
            self.completed_at = None

        super().save(*args, **kwargs)