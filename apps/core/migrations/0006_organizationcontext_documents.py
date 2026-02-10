from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_organizationcontext"),
        ("docs", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="organizationcontext",
            name="context_analysis_doc",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="context_analysis",
                to="docs.document",
                verbose_name="Analisis de contexto",
            ),
        ),
        migrations.AddField(
            model_name="organizationcontext",
            name="org_chart_doc",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="context_org_chart",
                to="docs.document",
                verbose_name="Organigrama",
            ),
        ),
        migrations.AddField(
            model_name="organizationcontext",
            name="process_map_doc",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="context_process_map",
                to="docs.document",
                verbose_name="Mapa de procesos",
            ),
        ),
        migrations.AddField(
            model_name="organizationcontext",
            name="quality_policy_doc",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="context_quality_policy",
                to="docs.document",
                verbose_name="Politica de calidad",
            ),
        ),
    ]
