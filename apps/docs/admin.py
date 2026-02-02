from django.contrib import admin
from .models import Document, DocumentVersion, DocumentApproval


class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 0
    fields = ("version_number", "status", "effective_date", "created_by", "created_at")
    readonly_fields = ("version_number", "status", "effective_date", "created_by", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Administración de documentos del SGC."""
    list_display = ('code', 'title', 'doc_type', 'process', 'is_active', 'created_at')
    list_filter = ('doc_type', 'process', 'is_active')
    search_fields = ('code', 'title')
    inlines = [DocumentVersionInline]
    fieldsets = (
        ('Información General', {
            'fields': ('code', 'title', 'doc_type')
        }),
        ('Clasificación', {
            'fields': ('process', 'owner')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Auditoría', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at',)


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    """Administración de versiones de documento."""
    list_display = ('document', 'version_number', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('document__code', 'version_number')
    fieldsets = (
        ('Documento', {
            'fields': ('document', 'version_number')
        }),
        ('Archivo', {
            'fields': ('file', 'notes')
        }),
        ('Vigencia', {
            'fields': ('effective_date', 'review_due_date')
        }),
        ('Estado', {
            'fields': ('status',)
        }),
        ('Auditoría', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_by', 'created_at', 'status')
    
    def save_model(self, request, obj, form, change):
        """Asignar automáticamente created_by con el usuario actual."""
        if not change:  # Si es nuevo (no es cambio)
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        """Hacer readonly todos los campos si status es APPROVED o OBSOLETE."""
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.status in (DocumentVersion.Status.APPROVED, DocumentVersion.Status.OBSOLETE):
            # Si la versión está aprobada u obsoleta, no se puede editar ningún campo
            readonly.extend(['document', 'version_number', 'file', 'notes', 'effective_date', 'review_due_date', 'status'])
        return readonly


@admin.register(DocumentApproval)
class DocumentApprovalAdmin(admin.ModelAdmin):
    """Administración de aprobaciones de documentos (solo lectura)."""
    list_display = ('document_version', 'approved_by', 'approved_at')
    readonly_fields = ('document_version', 'approved_by', 'approved_at', 'comment')
    fieldsets = (
        ('Aprobación', {
            'fields': ('document_version', 'approved_by', 'approved_at')
        }),
        ('Comentario', {
            'fields': ('comment',)
        }),
    )
    
    def has_add_permission(self, request):
        """No permitir agregar aprobaciones desde admin."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """No permitir editar aprobaciones."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """No permitir eliminar aprobaciones."""
        return False
