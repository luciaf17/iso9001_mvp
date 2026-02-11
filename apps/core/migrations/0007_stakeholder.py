from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_organizationcontext_documents"),
        ("docs", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Stakeholder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, verbose_name="Nombre")),
                ("stakeholder_type", models.CharField(choices=[("CUSTOMER", "Cliente"), ("SUPPLIER", "Proveedor"), ("INTERNAL", "Interno"), ("REGULATOR", "Regulador"), ("COMMUNITY", "Comunidad"), ("OTHER", "Otro")], max_length=20, verbose_name="Tipo")),
                ("expectations", models.TextField(verbose_name="Expectativas")),
                ("review_date", models.DateField(blank=True, null=True, verbose_name="Fecha de revision")),
                ("is_active", models.BooleanField(default=True, verbose_name="Activo")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Creado el")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Actualizado el")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="stakeholders", to="core.organization", verbose_name="Organizacion")),
                ("related_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="stakeholders", to="docs.document", verbose_name="Documento relacionado")),
                ("related_process", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="stakeholders", to="core.process", verbose_name="Proceso relacionado")),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="stakeholders", to="core.site", verbose_name="Sede")),
            ],
            options={
                "verbose_name": "Parte interesada",
                "verbose_name_plural": "Partes interesadas",
                "ordering": ["name"],
            },
        ),
    ]
