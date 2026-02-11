from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_stakeholder"),
        ("docs", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RiskOpportunity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200, verbose_name="Titulo")),
                ("description", models.TextField(verbose_name="Descripcion")),
                ("kind", models.CharField(choices=[("RISK", "Riesgo"), ("OPPORTUNITY", "Oportunidad")], max_length=20, verbose_name="Tipo")),
                ("probability", models.PositiveSmallIntegerField(choices=[(1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5")], verbose_name="Probabilidad")),
                ("impact", models.PositiveSmallIntegerField(choices=[(1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5")], verbose_name="Impacto")),
                ("score", models.PositiveSmallIntegerField(editable=False, verbose_name="Puntaje")),
                ("level", models.CharField(choices=[("LOW", "Bajo"), ("MEDIUM", "Medio"), ("HIGH", "Alto")], editable=False, max_length=10, verbose_name="Nivel")),
                ("treatment_plan", models.TextField(blank=True, verbose_name="Plan de tratamiento")),
                ("due_date", models.DateField(blank=True, null=True, verbose_name="Fecha limite")),
                ("status", models.CharField(choices=[("OPEN", "Abierto"), ("IN_PROGRESS", "En progreso"), ("CLOSED", "Cerrado")], default="OPEN", max_length=20, verbose_name="Estado")),
                ("is_active", models.BooleanField(default=True, verbose_name="Activo")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Creado el")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Actualizado el")),
                ("evidence_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="risks_opportunities", to="docs.document", verbose_name="Documento evidencia")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="risks_opportunities", to="core.organization", verbose_name="Organizacion")),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="risks_opportunities", to=settings.AUTH_USER_MODEL, verbose_name="Responsable")),
                ("related_process", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="risks_opportunities", to="core.process", verbose_name="Proceso relacionado")),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="risks_opportunities", to="core.site", verbose_name="Sede")),
                ("stakeholder", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="risks_opportunities", to="core.stakeholder", verbose_name="Parte interesada")),
            ],
            options={
                "verbose_name": "Riesgo u oportunidad",
                "verbose_name_plural": "Riesgos y oportunidades",
                "ordering": ["-updated_at"],
            },
        ),
    ]
