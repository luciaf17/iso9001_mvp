from django.contrib import admin

from .models import AuditEvent, Organization, Site, Process, Stakeholder, RiskOpportunity


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