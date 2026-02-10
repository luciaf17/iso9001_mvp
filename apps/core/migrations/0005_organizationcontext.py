from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_org_site_process_hierarchy"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OrganizationContext",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("review_date", models.DateField(blank=True, null=True, verbose_name="Fecha de revision")),
                ("summary", models.TextField(blank=True, verbose_name="Resumen")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Actualizado")),
                (
                    "organization",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="context",
                        to="core.organization",
                        verbose_name="Organizacion",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="organization_contexts",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Responsable",
                    ),
                ),
                (
                    "site",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="organization_contexts",
                        to="core.site",
                        verbose_name="Sede",
                    ),
                ),
            ],
        ),
    ]
