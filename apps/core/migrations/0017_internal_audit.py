from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("docs", "0002_document_processes_m2m"),
        ("core", "0016_update_objective_frequency"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="InternalAudit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200, verbose_name="Titulo")),
                ("audit_date", models.DateField(verbose_name="Fecha de auditoria")),
                ("scope", models.TextField(blank=True, verbose_name="Alcance")),
                ("auditee", models.CharField(blank=True, max_length=200, verbose_name="Auditado")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PLANNED", "Planificada"),
                            ("IN_PROGRESS", "En progreso"),
                            ("COMPLETED", "Completada"),
                            ("CANCELLED", "Cancelada"),
                        ],
                        default="PLANNED",
                        max_length=20,
                        verbose_name="Estado",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Creado el")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Actualizado el")),
                (
                    "auditor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audits_as_auditor",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Auditor",
                    ),
                ),
                (
                    "evidence_document",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="internal_audits_as_evidence",
                        to="docs.document",
                        verbose_name="Documento evidencia",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="internal_audits",
                        to="core.organization",
                        verbose_name="Organizacion",
                    ),
                ),
                (
                    "site",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="internal_audits",
                        to="core.site",
                        verbose_name="Sede",
                    ),
                ),
            ],
            options={
                "verbose_name": "Auditoria interna",
                "verbose_name_plural": "Auditorias internas",
                "ordering": ["-audit_date", "title"],
            },
        ),
        migrations.CreateModel(
            name="AuditQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "process_type",
                    models.CharField(
                        blank=True,
                        choices=[("STRATEGIC", "Estrategico"), ("MISSIONAL", "Misional"), ("SUPPORT", "Soporte")],
                        max_length=20,
                        null=True,
                        verbose_name="Tipo de proceso",
                    ),
                ),
                ("text", models.TextField(verbose_name="Pregunta")),
                ("is_active", models.BooleanField(default=True, verbose_name="Activa")),
                ("ordering", models.IntegerField(default=0, verbose_name="Orden")),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="audit_questions",
                        to="core.organization",
                        verbose_name="Organizacion",
                    ),
                ),
            ],
            options={
                "verbose_name": "Pregunta de auditoria",
                "verbose_name_plural": "Preguntas de auditoria",
                "ordering": ["ordering", "id"],
            },
        ),
        migrations.CreateModel(
            name="AuditFinding",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "finding_type",
                    models.CharField(
                        choices=[
                            ("OBSERVATION", "Observacion"),
                            ("NONCONFORMITY", "No conformidad"),
                            ("OPPORTUNITY", "Oportunidad"),
                        ],
                        max_length=20,
                        verbose_name="Tipo de hallazgo",
                    ),
                ),
                ("description", models.TextField(verbose_name="Descripcion")),
                (
                    "severity",
                    models.CharField(
                        blank=True,
                        choices=[("MINOR", "Menor"), ("MAJOR", "Mayor"), ("CRITICAL", "Critica")],
                        max_length=20,
                        null=True,
                        verbose_name="Severidad",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Creado el")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Actualizado el")),
                (
                    "audit",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="findings",
                        to="core.internalaudit",
                        verbose_name="Auditoria",
                    ),
                ),
                (
                    "nc",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_findings",
                        to="core.noconformity",
                        verbose_name="No conformidad",
                    ),
                ),
                (
                    "related_process",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_findings",
                        to="core.process",
                        verbose_name="Proceso relacionado",
                    ),
                ),
            ],
            options={
                "verbose_name": "Hallazgo de auditoria",
                "verbose_name_plural": "Hallazgos de auditoria",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="AuditAnswer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "result",
                    models.CharField(
                        choices=[("OK", "OK"), ("NOT_OK", "No OK"), ("NA", "No aplica")],
                        max_length=10,
                        verbose_name="Resultado",
                    ),
                ),
                ("notes", models.TextField(blank=True, verbose_name="Notas")),
                (
                    "audit",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="answers",
                        to="core.internalaudit",
                        verbose_name="Auditoria",
                    ),
                ),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="answers",
                        to="core.auditquestion",
                        verbose_name="Pregunta",
                    ),
                ),
            ],
            options={
                "verbose_name": "Respuesta de auditoria",
                "verbose_name_plural": "Respuestas de auditoria",
                "ordering": ["question__ordering", "id"],
                "unique_together": {("audit", "question")},
            },
        ),
        migrations.AddField(
            model_name="internalaudit",
            name="related_processes",
            field=models.ManyToManyField(
                blank=True,
                related_name="internal_audits",
                to="core.process",
                verbose_name="Procesos relacionados",
            ),
        ),
    ]
