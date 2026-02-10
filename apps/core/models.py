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
