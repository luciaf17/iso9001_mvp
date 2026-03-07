from django.contrib import admin

from .models import (
    AuditAnswer,
    AuditEvent,
    AuditFinding,
    AuditQuestion,
    CAPAAction,
    Competency,
    Employee,
    EmployeeCompetency,
    IndicatorMeasurement,
    InternalAudit,
    ManagementReview,
    NoConformity,
    NonconformingOutput,
    Organization,
    OrganizationContext,
    Process,
    QualityIndicator,
    QualityObjective,
    RiskOpportunity,
    Site,
    Stakeholder,
    Supplier,
    SupplierEvaluation,
    Training,
    TrainingAttendance,
)


class SupplierEvaluationInline(admin.TabularInline):
    model = SupplierEvaluation
    extra = 0
    readonly_fields = ("overall_score", "created_at")
    fields = (
        "evaluation_date",
        "evaluator",
        "quality_score",
        "delivery_score",
        "price_score",
        "overall_score",
        "decision",
        "notes",
        "evidence_file",
        "created_at",
    )


class IndicatorMeasurementInline(admin.TabularInline):
    model = IndicatorMeasurement
    extra = 0
    readonly_fields = ("created_at",)
    fields = ("measurement_date", "value", "notes", "created_at")


class TrainingAttendanceInline(admin.TabularInline):
    model = TrainingAttendance
    extra = 0
    fields = (
        "employee",
        "completion_status",
        "effectiveness_evaluated",
        "effectiveness_result",
        "evaluation_date",
        "notes",
    )


class EmployeeCompetencyInline(admin.TabularInline):
    model = EmployeeCompetency
    extra = 0
    readonly_fields = ("is_gap",)
    fields = (
        "competency",
        "level_required",
        "level_current",
        "is_gap",
        "last_evaluated",
    )


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "actor", "action", "object_type", "object_id")
    list_filter = ("action", "object_type", "timestamp")
    search_fields = ("action", "object_type", "actor__username")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("name",)


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "process_type",
        "level",
        "organization",
        "site",
        "parent",
        "is_active",
    )
    list_filter = ("organization", "site", "process_type", "level", "is_active")
    search_fields = ("code", "name")
    ordering = ("level", "code")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            kwargs["queryset"] = Process.objects.order_by("level", "code")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(OrganizationContext)
class OrganizationContextAdmin(admin.ModelAdmin):
    list_display = ("organization", "site", "owner", "review_date", "updated_at")
    list_filter = ("site", "review_date")
    search_fields = ("organization__name", "summary", "qms_scope")
    readonly_fields = ("updated_at",)


@admin.register(Stakeholder)
class StakeholderAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "stakeholder_type",
        "organization",
        "related_process",
        "review_date",
        "is_active",
    )
    list_filter = ("stakeholder_type", "organization", "is_active")
    search_fields = ("name", "expectations")


@admin.register(RiskOpportunity)
class RiskOpportunityAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "kind",
        "related_process",
        "stakeholder",
        "probability",
        "impact",
        "score",
        "level",
        "status",
        "due_date",
        "is_active",
    )
    list_filter = ("kind", "level", "status", "organization", "is_active")
    search_fields = ("title", "description", "treatment_plan")


@admin.register(NoConformity)
class NoConformityAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "title",
        "origin",
        "severity",
        "status",
        "detected_at",
        "owner",
    )
    list_filter = ("status", "severity", "origin", "organization", "site")
    search_fields = ("code", "title", "description")
    readonly_fields = ("code", "created_at", "updated_at")

    fieldsets = (
        (
            "Identificación",
            {
                "fields": (
                    "organization",
                    "site",
                    "code",
                    "title",
                    "description",
                )
            },
        ),
        (
            "Clasificación",
            {"fields": ("origin", "severity", "status")},
        ),
        (
            "Detección",
            {"fields": ("detected_at", "detected_by")},
        ),
        (
            "Responsabilidad",
            {"fields": ("owner", "due_date")},
        ),
        (
            "Vinculación",
            {"fields": ("related_process", "related_document")},
        ),
        (
            "Análisis y Acciones",
            {
                "fields": ("root_cause_analysis", "corrective_action"),
                "classes": ("collapse",),
            },
        ),
        (
            "Verificación de Eficacia",
            {
                "fields": ("verification_date", "is_effective", "verification_notes"),
                "classes": ("collapse",),
            },
        ),
        (
            "Evidencia y Cierre",
            {"fields": ("evidence_document", "closed_date", "closed_by")},
        ),
        (
            "Metadata",
            {
                "fields": ("is_active", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(CAPAAction)
class CAPAActionAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "no_conformity",
        "finding",
        "action_type",
        "status",
        "owner",
        "due_date",
        "completed_at",
    )
    list_filter = ("action_type", "status", "organization")
    search_fields = (
        "title",
        "description",
        "no_conformity__code",
        "no_conformity__title",
        "finding__description",
    )
    readonly_fields = ("organization", "completed_at", "created_at", "updated_at")


@admin.register(InternalAudit)
class InternalAuditAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "audit_date",
        "audit_type",
        "status",
        "auditor",
        "auditee",
        "organization",
    )
    list_filter = ("status", "audit_type", "organization", "site")
    search_fields = ("title", "auditee", "scope")
    filter_horizontal = ("related_processes",)


@admin.register(AuditQuestion)
class AuditQuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "process_type", "ordering", "is_active", "organization")
    list_filter = ("process_type", "is_active", "organization")
    search_fields = ("text",)


@admin.register(AuditAnswer)
class AuditAnswerAdmin(admin.ModelAdmin):
    list_display = ("audit", "question", "result")
    list_filter = ("result",)
    search_fields = ("audit__title", "question__text")


@admin.register(AuditFinding)
class AuditFindingAdmin(admin.ModelAdmin):
    list_display = (
        "audit",
        "related_process",
        "finding_type",
        "severity",
        "nc",
        "created_at",
    )
    list_filter = (
        "finding_type",
        "severity",
        "audit__organization",
        "audit__audit_date",
    )
    search_fields = ("audit__title", "description", "nc__code", "related_process__name")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Hallazgo",
            {
                "fields": (
                    "audit",
                    "related_process",
                    "finding_type",
                    "severity",
                    "description",
                    "nc",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(QualityObjective)
class QualityObjectiveAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "indicator",
        "target_value",
        "current_value",
        "status",
        "owner",
        "due_date",
        "organization",
    )
    list_filter = ("status", "organization", "site", "related_process")
    search_fields = ("title", "indicator", "description")
    readonly_fields = ("status", "created_at", "updated_at")


@admin.register(ManagementReview)
class ManagementReviewAdmin(admin.ModelAdmin):
    list_display = (
        "review_date",
        "chairperson",
        "organization",
        "is_active",
        "created_at",
    )
    list_filter = ("organization", "review_date", "is_active")
    search_fields = (
        "organization__name",
        "chairperson__username",
        "chairperson__first_name",
        "chairperson__last_name",
        "attendees",
    )
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Reunión",
            {
                "fields": (
                    "organization",
                    "review_date",
                    "chairperson",
                    "attendees",
                )
            },
        ),
        (
            "Entradas (ISO 9.3.2)",
            {
                "fields": (
                    "audit_results_summary",
                    "customer_feedback_summary",
                    "process_performance_summary",
                    "nonconformities_status_summary",
                    "risk_opportunity_status_summary",
                    "supplier_performance_summary",
                    "resource_adequacy_summary",
                )
            },
        ),
        (
            "Salidas (ISO 9.3.3)",
            {
                "fields": (
                    "improvement_actions",
                    "changes_to_qms",
                    "resource_needs",
                )
            },
        ),
        (
            "Evidencia",
            {
                "fields": ("meeting_minutes_file",)
            },
        ),
        (
            "Metadata",
            {
                "fields": ("is_active", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(QualityIndicator)
class QualityIndicatorAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organization",
        "related_process",
        "frequency",
        "comparison_type",
        "target_value",
        "is_active",
    )
    list_filter = ("organization", "frequency", "comparison_type", "is_active")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")
    inlines = [IndicatorMeasurementInline]


@admin.register(IndicatorMeasurement)
class IndicatorMeasurementAdmin(admin.ModelAdmin):
    list_display = ("indicator", "measurement_date", "value", "created_at")
    list_filter = ("indicator__organization", "measurement_date")
    search_fields = ("indicator__name", "notes")
    readonly_fields = ("created_at",)


@admin.register(NonconformingOutput)
class NonconformingOutputAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "product_or_service",
        "organization",
        "severity",
        "disposition",
        "status",
        "detected_at",
        "closed_at",
        "is_active",
    )
    list_filter = ("organization", "severity", "disposition", "status", "is_active")
    search_fields = ("code", "product_or_service", "description")
    readonly_fields = ("code", "created_at", "updated_at")


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organization",
        "category",
        "status",
        "last_evaluation_date",
        "next_evaluation_date",
        "is_active",
    )
    list_filter = ("organization", "category", "status", "is_active")
    search_fields = ("name", "cuit", "contact_name", "contact_email")
    readonly_fields = ("last_evaluation_date", "created_at", "updated_at")
    inlines = [SupplierEvaluationInline]


@admin.register(SupplierEvaluation)
class SupplierEvaluationAdmin(admin.ModelAdmin):
    list_display = (
        "supplier",
        "evaluation_date",
        "evaluator",
        "overall_score",
        "decision",
        "created_at",
    )
    list_filter = ("decision", "evaluation_date", "organization")
    search_fields = ("supplier__name", "notes")
    readonly_fields = ("overall_score", "created_at")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "position",
        "department",
        "email",
        "organization",
        "is_active",
    )
    list_filter = ("organization", "department", "is_active")
    search_fields = ("first_name", "last_name", "email", "position")
    readonly_fields = ("created_at", "updated_at")
    inlines = [EmployeeCompetencyInline]


@admin.register(Competency)
class CompetencyAdmin(admin.ModelAdmin):
    list_display = ("name", "required_for_position", "organization", "created_at")
    list_filter = ("organization", "required_for_position")
    search_fields = ("name", "description", "required_for_position")
    readonly_fields = ("created_at",)


@admin.register(EmployeeCompetency)
class EmployeeCompetencyAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "competency",
        "level_required",
        "level_current",
        "is_gap",
        "last_evaluated",
    )
    list_filter = ("is_gap", "employee__organization", "last_evaluated")
    search_fields = ("employee__first_name", "employee__last_name", "competency__name")
    readonly_fields = ("is_gap",)


@admin.register(Training)
class TrainingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "organization",
        "provider",
        "training_date",
        "expiration_date",
        "created_at",
    )
    list_filter = ("organization", "training_date", "expiration_date")
    search_fields = ("title", "provider", "description")
    readonly_fields = ("created_at",)
    inlines = [TrainingAttendanceInline]


@admin.register(TrainingAttendance)
class TrainingAttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "training",
        "employee",
        "completion_status",
        "effectiveness_evaluated",
        "effectiveness_result",
        "evaluation_date",
    )
    list_filter = (
        "completion_status",
        "effectiveness_evaluated",
        "effectiveness_result",
        "training__organization",
    )
    search_fields = (
        "training__title",
        "employee__first_name",
        "employee__last_name",
        "notes",
    )
