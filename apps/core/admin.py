from django.contrib import admin

from .models import AuditEvent, Organization, Site, Process, Stakeholder, RiskOpportunity, NoConformity, CAPAAction


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    """Administración de eventos de auditoría (solo lectura)."""
    
    list_display = ('timestamp', 'actor', 'action', 'object_type', 'object_id')
    list_filter = ('action', 'object_type', 'timestamp')
    search_fields = ('action', 'object_type', 'actor__username')
    
    # Solo lectura - no permitir agregar, editar o eliminar
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

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
            "Identificacion",
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
            "Clasificacion",
            {"fields": ("origin", "severity", "status")},
        ),
        (
            "Deteccion",
            {"fields": ("detected_at", "detected_by")},
        ),
        (
            "Responsabilidad",
            {"fields": ("owner", "due_date")},
        ),
        (
            "Vinculacion",
            {"fields": ("related_process", "related_document")},
        ),
        (
            "Analisis y Acciones (ISO 10.2)",
            {
                "fields": ("root_cause_analysis", "corrective_action"),
                "classes": ("collapse",),
            },
        ),
        (
            "Verificacion de Eficacia",
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
        "action_type",
        "status",
        "owner",
        "due_date",
        "completed_at",
    )
    list_filter = (
        "action_type",
        "status",
        "organization",
    )
    search_fields = (
        "title",
        "description",
        "no_conformity__code",
        "no_conformity__title",
    )
    readonly_fields = ("organization", "completed_at", "created_at", "updated_at")

    fieldsets = (
        (
            "Vinculacion",
            {"fields": ("no_conformity", "organization")},
        ),
        (
            "Informacion",
            {"fields": ("title", "description", "action_type")},
        ),
        (
            "Responsabilidad",
            {"fields": ("owner", "due_date", "status")},
        ),
        (
            "Completitud",
            {"fields": ("completed_at", "completion_notes", "evidence_document")},
        ),
        (
            "Metadata",
            {
                "fields": ("is_active", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )