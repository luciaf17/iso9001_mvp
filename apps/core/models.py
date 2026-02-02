from django.db import models
from django.conf import settings


class Process(models.Model):
    """Proceso del Sistema de Gestión de la Calidad."""
    
    code = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Código",
        help_text="Identificador único del proceso (ej: CAL, VEN, etc.)"
    )
    name = models.CharField(
        max_length=120,
        unique=True,
        verbose_name="Nombre"
    )
    
    class Meta:
        ordering = ["code"]
        verbose_name = "Proceso"
        verbose_name_plural = "Procesos"
    
    def __str__(self):
        return f"{self.code} - {self.name}"


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
