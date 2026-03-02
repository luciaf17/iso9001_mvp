from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from datetime import date, timedelta


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
    severity_score = models.IntegerField(
        default=0,
        verbose_name="Score de criticidad",
        help_text="Puntuación automática basada en severidad (1=Menor, 2=Mayor, 3=Crítica)",
        editable=False,
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
        
        # Validación cruzada: No cerrar si hay CAPA abiertas
        if self.status == self.Status.CLOSED:
            open_capa = self.capa_actions.exclude(status="DONE")
            if open_capa.exists():
                raise ValidationError(
                    "No se puede cerrar la NC mientras existan acciones CAPA abiertas o en progreso. "
                    f"Hay {open_capa.count()} CAPA pendientes."
                )

    def save(self, *args, **kwargs):
        from django.utils import timezone

        # Auto-calculate severity_score based on severity
        severity_map = {
            self.Severity.MINOR: 1,
            self.Severity.MAJOR: 2,
            self.Severity.CRITICAL: 3,
        }
        self.severity_score = severity_map.get(self.severity, 0)

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
        null=True,
        blank=True,
        related_name="capa_actions",
        verbose_name="No conformidad",
    )
    finding = models.ForeignKey(
        "core.AuditFinding",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="capa_actions",
        verbose_name="Hallazgo asociado",
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

    class EffectivenessResult(models.TextChoices):
        EFFECTIVE = "EFFECTIVE", "Efectiva"
        NOT_EFFECTIVE = "NOT_EFFECTIVE", "No efectiva"

    effectiveness_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de evaluacion de eficacia",
    )
    effectiveness_result = models.CharField(
        max_length=20,
        choices=EffectivenessResult.choices,
        null=True,
        blank=True,
        verbose_name="Resultado de eficacia",
    )
    effectiveness_notes = models.TextField(
        blank=True,
        verbose_name="Notas de eficacia",
        help_text="Detalles sobre la evaluacion de eficacia de la accion",
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
        if self.no_conformity_id:
            return f"{self.get_action_type_display()}: {self.title} (NC: {self.no_conformity.code})"
        elif self.finding_id:
            return f"{self.get_action_type_display()}: {self.title} (Hallazgo: {self.finding.id})"
        else:
            return f"{self.get_action_type_display()}: {self.title}"

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Exactly one of no_conformity or finding must be set
        has_nc = bool(self.no_conformity_id)
        has_finding = bool(self.finding_id)
        
        if not has_nc and not has_finding:
            raise ValidationError("CAPAAction debe estar vinculada a una NC o a un Hallazgo de auditoría.")
        
        if has_nc and has_finding:
            raise ValidationError("CAPAAction no puede estar vinculada a ambas: NC y Hallazgo. Elige uno.")
        
        # Validate organization consistency
        if has_nc and self.no_conformity and self.organization:
            if self.no_conformity.organization_id != self.organization_id:
                raise ValidationError("La organización de la NC no coincide con la de la acción CAPA.")
        
        if has_finding and self.finding and self.organization:
            if self.finding.audit.organization_id != self.organization_id:
                raise ValidationError("La organización del hallazgo no coincide con la de la acción CAPA.")

    def save(self, *args, **kwargs):
        from django.utils import timezone

        # Auto-derive organization if not set
        if not self.organization_id:
            if self.no_conformity_id:
                self.organization = self.no_conformity.organization
            elif self.finding_id:
                self.organization = self.finding.audit.organization

        if self.status == self.Status.DONE and not self.completed_at:
            self.completed_at = timezone.now()

        if self.status in [self.Status.OPEN, self.Status.IN_PROGRESS] and self.completed_at:
            self.completed_at = None

        super().save(*args, **kwargs)
        
        # Auto-cierre de NC cuando todas las CAPA estén DONE
        if self.status == self.Status.DONE and self.no_conformity_id:
            nc = self.no_conformity
            # Verificar si todas las CAPA están DONE
            open_capa = nc.capa_actions.exclude(status=self.Status.DONE)
            if not open_capa.exists() and nc.status == nc.Status.IN_TREATMENT:
                # Auto-transicionar a VERIFICATION
                nc.status = nc.Status.VERIFICATION
                nc.verification_date = timezone.now().date()
                nc.save(update_fields=['status', 'verification_date'])


class InternalAudit(models.Model):
    """Auditoria interna planificada (ISO 9001 9.2)."""

    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planificada"
        IN_PROGRESS = "IN_PROGRESS", "En progreso"
        COMPLETED = "COMPLETED", "Completada"
        CANCELLED = "CANCELLED", "Cancelada"

    class AuditType(models.TextChoices):
        INTERNAL = "INTERNAL", "Interna"
        EXTERNAL = "EXTERNAL", "Externa"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="internal_audits",
        verbose_name="Organizacion",
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internal_audits",
        verbose_name="Sede",
    )
    title = models.CharField(
        max_length=200,
        verbose_name="Titulo",
    )
    audit_date = models.DateField(
        verbose_name="Fecha de auditoria",
    )
    audit_type = models.CharField(
        max_length=10,
        choices=AuditType.choices,
        default=AuditType.INTERNAL,
        verbose_name="Tipo de auditoria",
    )
    scope = models.TextField(
        blank=True,
        verbose_name="Alcance",
    )
    auditor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audits_as_auditor",
        verbose_name="Auditor",
    )
    auditee = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Auditado",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
        verbose_name="Estado",
    )
    related_processes = models.ManyToManyField(
        Process,
        blank=True,
        related_name="internal_audits",
        verbose_name="Procesos relacionados",
    )
    evidence_document = models.ForeignKey(
        "docs.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internal_audits_as_evidence",
        verbose_name="Documento evidencia",
    )
    plan_file = models.FileField(
        upload_to="audits/plan/",
        null=True,
        blank=True,
        verbose_name="Archivo de planificacion",
    )
    report_file = models.FileField(
        upload_to="audits/report/",
        null=True,
        blank=True,
        verbose_name="Archivo de informe",
    )
    team_cv_file = models.FileField(
        upload_to="audits/team_cv/",
        null=True,
        blank=True,
        verbose_name="CV del equipo auditor",
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
        ordering = ["-audit_date", "title"]
        verbose_name = "Auditoria interna"
        verbose_name_plural = "Auditorias internas"

    def __str__(self):
        return f"{self.title} ({self.audit_date})"


class AuditQuestion(models.Model):
    """Pregunta reusable para checklist de auditoria."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="audit_questions",
        verbose_name="Organizacion",
    )
    process_type = models.CharField(
        max_length=20,
        choices=Process.ProcessType.choices,
        null=True,
        blank=True,
        verbose_name="Tipo de proceso",
    )
    text = models.TextField(
        verbose_name="Pregunta",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activa",
    )
    ordering = models.IntegerField(
        default=0,
        verbose_name="Orden",
    )

    class Meta:
        ordering = ["ordering", "id"]
        verbose_name = "Pregunta de auditoria"
        verbose_name_plural = "Preguntas de auditoria"

    def __str__(self):
        return self.text


class AuditAnswer(models.Model):
    """Respuesta a pregunta de auditoria."""

    class Result(models.TextChoices):
        OK = "OK", "OK"
        NOT_OK = "NOT_OK", "No OK"
        NA = "NA", "No aplica"

    audit = models.ForeignKey(
        InternalAudit,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="Auditoria",
    )
    question = models.ForeignKey(
        AuditQuestion,
        on_delete=models.PROTECT,
        related_name="answers",
        verbose_name="Pregunta",
    )
    result = models.CharField(
        max_length=10,
        choices=Result.choices,
        verbose_name="Resultado",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notas",
    )

    class Meta:
        ordering = ["question__ordering", "id"]
        unique_together = ("audit", "question")
        verbose_name = "Respuesta de auditoria"
        verbose_name_plural = "Respuestas de auditoria"

    def __str__(self):
        return f"{self.audit} - {self.question}"


class AuditFinding(models.Model):
    """Hallazgo de una auditoria."""

    class FindingType(models.TextChoices):
        AREA_OF_CONCERN = "AREA_OF_CONCERN", "Área de preocupación"
        IMPROVEMENT_OPPORTUNITY = "IMPROVEMENT_OPPORTUNITY", "Oportunidad de mejora"
        NONCONFORMITY = "NONCONFORMITY", "No conformidad"

    class Severity(models.TextChoices):
        MINOR = "MINOR", "Menor"
        MAJOR = "MAJOR", "Mayor"
        CRITICAL = "CRITICAL", "Critica"

    audit = models.ForeignKey(
        InternalAudit,
        on_delete=models.CASCADE,
        related_name="findings",
        verbose_name="Auditoria",
    )
    related_process = models.ForeignKey(
        Process,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_findings",
        verbose_name="Proceso relacionado",
    )
    finding_type = models.CharField(
        max_length=23,
        choices=FindingType.choices,
        verbose_name="Tipo de hallazgo",
    )
    description = models.TextField(
        verbose_name="Descripcion",
    )
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        null=True,
        blank=True,
        verbose_name="Severidad",
    )
    nc = models.ForeignKey(
        NoConformity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_findings",
        verbose_name="No conformidad",
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
        ordering = ["-created_at"]
        verbose_name = "Hallazgo de auditoria"
        verbose_name_plural = "Hallazgos de auditoria"

    def __str__(self):
        return f"{self.get_finding_type_display()} - {self.audit}"


class QualityObjective(models.Model):
    """Objetivo de calidad medible segun ISO 9001 clausula 6.2."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Activo"
        ACHIEVED = "ACHIEVED", "Cumplido"
        OVERDUE = "OVERDUE", "Vencido"
        CANCELLED = "CANCELLED", "Cancelado"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="quality_objectives",
        verbose_name="Organizacion",
    )

    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quality_objectives",
        verbose_name="Sede",
    )

    related_process = models.ForeignKey(
        Process,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quality_objectives",
        verbose_name="Proceso relacionado",
    )

    title = models.CharField(
        max_length=200,
        verbose_name="Titulo",
    )

    description = models.TextField(
        verbose_name="Descripcion",
    )

    indicator = models.CharField(
        max_length=200,
        verbose_name="Indicador",
        help_text="Ej: % entregas en termino",
    )

    target_value = models.FloatField(
        verbose_name="Valor meta",
        help_text="Valor objetivo a alcanzar",
    )

    current_value = models.FloatField(
        default=0,
        verbose_name="Valor actual",
    )

    unit = models.CharField(
        max_length=50,
        verbose_name="Unidad",
        help_text="Ej: %, días, unidades, horas",
    )

    class Frequency(models.TextChoices):
        WEEKLY = "WEEKLY", "Semanal"
        BIWEEKLY = "BIWEEKLY", "Quincenal"
        MONTHLY = "MONTHLY", "Mensual"
        BIMONTHLY = "BIMONTHLY", "Bimestral"
        QUARTERLY = "QUARTERLY", "Trimestral"
        SEMIANNUAL = "SEMIANNUAL", "Semestral"
        ANNUAL = "ANNUAL", "Anual"
        OTHER = "OTHER", "Otra"

    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        verbose_name="Frecuencia",
        help_text="Frecuencia de medicion del objetivo",
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quality_objectives",
        verbose_name="Responsable",
    )

    start_date = models.DateField(
        verbose_name="Fecha inicio",
    )

    due_date = models.DateField(
        verbose_name="Fecha vencimiento",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Estado",
        editable=False,
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
        ordering = ["due_date"]
        verbose_name = "Objetivo de calidad"
        verbose_name_plural = "Objetivos de calidad"

    def __str__(self):
        return f"{self.title} ({self.organization})"

    def calculate_status(self):
        """Calcula el estado basado en valores y fechas."""
        from django.utils import timezone

        if self.current_value >= self.target_value:
            return self.Status.ACHIEVED
        if timezone.now().date() > self.due_date:
            return self.Status.OVERDUE
        return self.Status.ACTIVE

    def save(self, *args, **kwargs):
        """Actualiza status automaticamente antes de guardar."""
        # Respetar CANCELLED: no recalcular si fue cancelado manualmente
        if self.status != self.Status.CANCELLED:
            self.status = self.calculate_status()
        super().save(*args, **kwargs)


class ManagementReview(models.Model):
    """Revision por la Direccion (ISO 9001 clausula 9.3)."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="management_reviews",
        verbose_name="Organizacion",
    )
    review_date = models.DateField(
        verbose_name="Fecha de revision",
    )
    chairperson = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="management_reviews_as_chair",
        verbose_name="Presidente",
    )
    attendees = models.TextField(
        blank=True,
        verbose_name="Asistentes",
        help_text="Lista de asistentes a la reunion",
    )

    # Entradas (ISO 9.3.2)
    audit_results_summary = models.TextField(
        blank=True,
        verbose_name="Resultados de auditorias",
        help_text="Resumen de resultados de auditorias internas y externas",
    )
    customer_feedback_summary = models.TextField(
        blank=True,
        verbose_name="Retroalimentacion del cliente",
        help_text="Resumen de retroalimentacion de clientes y partes interesadas",
    )
    process_performance_summary = models.TextField(
        blank=True,
        verbose_name="Desempeno de procesos",
        help_text="Resumen del desempeno y conformidad de productos/servicios",
    )
    nonconformities_status_summary = models.TextField(
        blank=True,
        verbose_name="Estado de no conformidades",
        help_text="Estado de no conformidades y acciones correctivas/preventivas",
    )
    risk_opportunity_status_summary = models.TextField(
        blank=True,
        verbose_name="Estado de riesgos y oportunidades",
        help_text="Estado de riesgos y oportunidades identificados",
    )
    supplier_performance_summary = models.TextField(
        blank=True,
        verbose_name="Desempeno de proveedores",
        help_text="Resumen del desempeno de proveedores externos",
    )
    resource_adequacy_summary = models.TextField(
        blank=True,
        verbose_name="Adecuacion de recursos",
        help_text="Adecuacion de recursos disponibles",
    )

    # Salidas (ISO 9.3.3)
    improvement_actions = models.TextField(
        blank=True,
        verbose_name="Oportunidades de mejora",
        help_text="Decisiones y acciones relacionadas con oportunidades de mejora",
    )
    changes_to_qms = models.TextField(
        blank=True,
        verbose_name="Cambios al SGC",
        help_text="Cambios necesarios al Sistema de Gestion de Calidad",
    )
    resource_needs = models.TextField(
        blank=True,
        verbose_name="Necesidades de recursos",
        help_text="Necesidades de recursos identificadas",
    )

    # Evidencia
    meeting_minutes_file = models.FileField(
        upload_to="management_reviews/",
        null=True,
        blank=True,
        verbose_name="Acta de reunion",
    )

    # Metadata
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
        ordering = ["-review_date"]
        verbose_name = "Revision por la Direccion"
        verbose_name_plural = "Revisiones por la Direccion"

    def __str__(self):
        return f"Revision {self.review_date} - {self.organization}"


class QualityIndicator(models.Model):
    """Indicadores de desempeño del SGC (ISO 9001 9.1)."""

    class Frequency(models.TextChoices):
        MONTHLY = "MONTHLY", "Mensual"
        QUARTERLY = "QUARTERLY", "Trimestral"
        YEARLY = "YEARLY", "Anual"

    class ComparisonType(models.TextChoices):
        GREATER_EQUAL = "GREATER_EQUAL", "Mayor o igual a"
        LESS_EQUAL = "LESS_EQUAL", "Menor o igual a"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="quality_indicators",
        verbose_name="Organización",
    )
    related_process = models.ForeignKey(
        Process,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quality_indicators",
        verbose_name="Proceso relacionado",
    )
    name = models.CharField(
        max_length=200,
        verbose_name="Nombre",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Descripción",
    )
    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        verbose_name="Frecuencia de medición",
    )
    target_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Valor meta",
    )
    comparison_type = models.CharField(
        max_length=20,
        choices=ComparisonType.choices,
        verbose_name="Tipo de comparación",
    )
    unit = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Unidad",
        help_text="Por ejemplo: %, puntos, días, etc.",
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
        verbose_name = "Indicador de Calidad"
        verbose_name_plural = "Indicadores de Calidad"

    def __str__(self):
        return f"{self.name} ({self.organization})"

    def get_last_measurement(self):
        """Devuelve la última medición registrada."""
        return self.measurements.first()

    def get_last_n_measurements(self, n=12):
        """Devuelve las últimas n mediciones."""
        return self.measurements.all()[:n]

    def get_status(self):
        """
        Calcula estado automático del indicador:
        - NO_DATA: No hay mediciones registradas
        - OVERDUE: No hay mediciones recientes según frecuencia
        - OUT_OF_TARGET: Última medición fuera de meta
        - OK: Última medición dentro de meta
        """
        last_measurement = self.get_last_measurement()
        
        # No hay mediciones
        if not last_measurement:
            return "NO_DATA"
        
        # Calcular diferencia de días
        days_since_measurement = (date.today() - last_measurement.measurement_date).days
        
        # Verificar si está vencido según frecuencia
        frequency_limits = {
            self.Frequency.MONTHLY: 31,
            self.Frequency.QUARTERLY: 93,
            self.Frequency.YEARLY: 366,
        }
        
        max_days = frequency_limits.get(self.frequency, 31)
        if days_since_measurement > max_days:
            return "OVERDUE"
        
        # Verificar si cumple la meta
        if not last_measurement.is_within_target():
            return "OUT_OF_TARGET"
        
        return "OK"


class IndicatorMeasurement(models.Model):
    """Medición de un indicador de calidad."""

    indicator = models.ForeignKey(
        QualityIndicator,
        on_delete=models.CASCADE,
        related_name="measurements",
        verbose_name="Indicador",
    )
    measurement_date = models.DateField(
        verbose_name="Fecha de medición",
    )
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Valor medido",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notas",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado el",
    )

    class Meta:
        ordering = ["-measurement_date"]
        verbose_name = "Medición de Indicador"
        verbose_name_plural = "Mediciones de Indicador"

    def __str__(self):
        return f"{self.indicator.name} - {self.measurement_date}"

    def is_within_target(self):
        """Verifica si la medición cumple con la meta."""
        if self.indicator.comparison_type == QualityIndicator.ComparisonType.GREATER_EQUAL:
            return self.value >= self.indicator.target_value
        return self.value <= self.indicator.target_value


class NonconformingOutput(models.Model):
    """Producto/Servicio No Conforme (ISO 9001 8.7)."""

    class Severity(models.TextChoices):
        MINOR = "MINOR", "Menor"
        MAJOR = "MAJOR", "Mayor"
        CRITICAL = "CRITICAL", "Crítica"

    class Disposition(models.TextChoices):
        REWORK = "REWORK", "Retrabajo"
        REPAIR = "REPAIR", "Reparación"
        SCRAP = "SCRAP", "Descarte"
        CONCESSION = "CONCESSION", "Concesión/Aceptación"
        RETURN = "RETURN", "Devolución"
        OTHER = "OTHER", "Otro"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Abierta"
        IN_TREATMENT = "IN_TREATMENT", "En tratamiento"
        CLOSED = "CLOSED", "Cerrada"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="nonconforming_outputs",
        verbose_name="Organización",
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nonconforming_outputs",
        verbose_name="Sede",
    )
    related_process = models.ForeignKey(
        Process,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nonconforming_outputs",
        verbose_name="Proceso relacionado",
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Código",
        help_text="PNC-2026-001, PNC-2026-002, etc.",
        editable=False,
    )
    detected_at = models.DateField(
        verbose_name="Fecha de detección",
    )
    detected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="detected_nonconforming_outputs",
        verbose_name="Detectado por",
    )
    product_or_service = models.CharField(
        max_length=200,
        verbose_name="Producto/Servicio",
        help_text="Ejemplo: Tolva 26tn, Servicio postventa",
    )
    description = models.TextField(
        verbose_name="Descripción del no cumplimiento",
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Cantidad",
    )
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.MAJOR,
        verbose_name="Severidad",
    )
    disposition = models.CharField(
        max_length=20,
        choices=Disposition.choices,
        null=True,
        blank=True,
        verbose_name="Disposición",
        help_text="Acción tomada sobre el producto/servicio no conforme",
    )
    disposition_notes = models.TextField(
        blank=True,
        verbose_name="Notas sobre disposición",
        help_text="Detalles y evidencia de la disposición (obligatorio para CONCESSION)",
    )
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="treated_nonconforming_outputs",
        verbose_name="Responsable del tratamiento",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        verbose_name="Estado",
    )
    closed_at = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de cierre",
    )
    evidence_file = models.FileField(
        upload_to="nonconforming_outputs/",
        null=True,
        blank=True,
        verbose_name="Archivo de evidencia",
    )
    linked_nc = models.ForeignKey(
        NoConformity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nonconforming_outputs",
        verbose_name="NC vinculada",
        help_text="Opcionalmente linkear a NoConformity del sistema",
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
        ordering = ["-detected_at"]
        verbose_name = "Producto/Servicio No Conforme"
        verbose_name_plural = "Productos/Servicios No Conformes"

    def __str__(self):
        return f"{self.code}: {self.product_or_service}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.status == self.Status.CLOSED and not self.disposition:
            raise ValidationError({
                "disposition": "Debe especificar la disposición antes de cerrar."
            })

        if self.disposition == self.Disposition.CONCESSION and not self.disposition_notes:
            raise ValidationError({
                "disposition_notes": "La disposición CONCESIÓN requiere notas obligatoriamente."
            })

    def save(self, *args, **kwargs):
        from django.utils import timezone

        # Auto-generar código
        if not self.code:
            year = timezone.now().year
            last_pnc = NonconformingOutput.objects.filter(
                organization=self.organization,
                code__startswith=f"PNC-{year}",
            ).order_by("-code").first()

            if last_pnc and last_pnc.code:
                try:
                    last_num = int(last_pnc.code.split("-")[-1])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1

            self.code = f"PNC-{year}-{new_num:03d}"

        # Auto-setear closed_at al cerrar
        if self.status == self.Status.CLOSED and not self.closed_at:
            self.closed_at = timezone.now().date()

        super().save(*args, **kwargs)


class Supplier(models.Model):
    """Proveedor (ISO 9001 8.4)."""

    class Category(models.TextChoices):
        RAW_MATERIAL = "RAW_MATERIAL", "Materia Prima"
        SERVICE = "SERVICE", "Servicio"
        OUTSOURCED_PROCESS = "OUTSOURCED_PROCESS", "Proceso Tercerizado"
        OTHER = "OTHER", "Otro"

    class Status(models.TextChoices):
        APPROVED = "APPROVED", "Aprobado"
        CONDITIONAL = "CONDITIONAL", "Aprobado Condicionalmente"
        NOT_APPROVED = "NOT_APPROVED", "No Aprobado"
        PENDING = "PENDING", "Pendiente"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="suppliers",
        verbose_name="Organización",
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suppliers",
        verbose_name="Sede",
    )
    related_process = models.ForeignKey(
        Process,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suppliers",
        verbose_name="Proceso Relacionado",
    )
    name = models.CharField(
        max_length=200,
        verbose_name="Nombre del Proveedor",
    )
    cuit = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="CUIT",
    )
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        verbose_name="Categoría",
    )
    contact_name = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Nombre de Contacto",
    )
    contact_email = models.EmailField(
        blank=True,
        verbose_name="Email de Contacto",
    )
    contact_phone = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Teléfono de Contacto",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Estado",
    )
    last_evaluation_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Última Evaluación",
        editable=False,
    )
    next_evaluation_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Próxima Evaluación",
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
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_supplier_per_org",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    @property
    def is_evaluation_overdue(self):
        """Verifica si la evaluación está vencida."""
        if not self.next_evaluation_date:
            return False
        return self.next_evaluation_date < date.today()


class SupplierEvaluation(models.Model):
    """Evaluación de Proveedor (ISO 9001 8.4)."""

    class Decision(models.TextChoices):
        APPROVED = "APPROVED", "Aprobado"
        CONDITIONAL = "CONDITIONAL", "Aprobado Condicionalmente"
        NOT_APPROVED = "NOT_APPROVED", "No Aprobado"

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="evaluations",
        verbose_name="Proveedor",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="supplier_evaluations",
        verbose_name="Organización",
    )
    evaluation_date = models.DateField(
        verbose_name="Fecha de Evaluación",
    )
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supplier_evaluations",
        verbose_name="Evaluador",
    )
    quality_score = models.PositiveSmallIntegerField(
        verbose_name="Puntuación Calidad (1-5)",
        help_text="Calidad de productos/servicios (1=Muy malo, 5=Excelente)",
    )
    delivery_score = models.PositiveSmallIntegerField(
        verbose_name="Puntuación Entrega (1-5)",
        help_text="Cumplimiento de plazos de entrega (1=Muy malo, 5=Excelente)",
    )
    price_score = models.PositiveSmallIntegerField(
        verbose_name="Puntuación Precio (1-5)",
        help_text="Relación precio-calidad (1=Muy caro, 5=Muy competitivo)",
    )
    overall_score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        verbose_name="Puntuación General",
        editable=False,
    )
    decision = models.CharField(
        max_length=20,
        choices=Decision.choices,
        verbose_name="Decisión",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notas",
    )
    evidence_file = models.FileField(
        upload_to="supplier_evaluations/",
        null=True,
        blank=True,
        verbose_name="Archivo de Evidencia",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado el",
    )

    class Meta:
        ordering = ["-evaluation_date"]
        verbose_name = "Evaluación de Proveedor"
        verbose_name_plural = "Evaluaciones de Proveedor"

    def __str__(self):
        return f"{self.supplier.name} - {self.evaluation_date}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if not (1 <= self.quality_score <= 5):
            raise ValidationError({"quality_score": "La puntuación debe ser entre 1 y 5."})
        if not (1 <= self.delivery_score <= 5):
            raise ValidationError({"delivery_score": "La puntuación debe ser entre 1 y 5."})
        if not (1 <= self.price_score <= 5):
            raise ValidationError({"price_score": "La puntuación debe ser entre 1 y 5."})

    def save(self, *args, **kwargs):
        from django.utils import timezone
        from datetime import timedelta

        # Auto-completar organización desde supplier
        if not self.organization:
            self.organization = self.supplier.organization

        # Calcular overall_score
        self.overall_score = round(
            (self.quality_score + self.delivery_score + self.price_score) / 3,
            2
        )

        # Actualizar supplier status y fechas
        self.supplier.status = self.decision
        self.supplier.last_evaluation_date = self.evaluation_date

        # Setear próxima evaluación si está vacía
        if not self.supplier.next_evaluation_date:
            if self.decision == self.Decision.APPROVED:
                months = 12
            elif self.decision == self.Decision.CONDITIONAL:
                months = 6
            else:  # NOT_APPROVED
                months = 3
            
            next_date = self.evaluation_date + timedelta(days=30 * months)
            self.supplier.next_evaluation_date = next_date

        self.supplier.save()
        super().save(*args, **kwargs)