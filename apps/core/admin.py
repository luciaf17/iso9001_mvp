from django.contrib import admin
from .models import AuditEvent
from django.contrib import admin
from .models import Process


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
    list_display = ("code", "name")
    search_fields = ("code", "name")