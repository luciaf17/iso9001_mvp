from django.db import migrations, models
from django.utils import timezone


def populate_nc_codes(apps, schema_editor):
    NoConformity = apps.get_model("core", "NoConformity")
    db_alias = schema_editor.connection.alias

    max_numbers = {}
    existing_qs = (
        NoConformity.objects.using(db_alias)
        .exclude(code__isnull=True)
        .exclude(code="")
        .only("code", "organization_id")
    )

    for nc in existing_qs:
        if not nc.code:
            continue
        parts = nc.code.split("-")
        if len(parts) < 3 or parts[0] != "NC":
            continue
        try:
            year = int(parts[1])
            number = int(parts[2])
        except (ValueError, IndexError):
            continue
        key = (nc.organization_id, year)
        current_max = max_numbers.get(key, 0)
        if number > current_max:
            max_numbers[key] = number

    missing_qs = (
        NoConformity.objects.using(db_alias)
        .filter(models.Q(code__isnull=True) | models.Q(code=""))
        .only("id", "organization_id", "created_at")
        .order_by("created_at", "id")
    )

    for nc in missing_qs:
        year = nc.created_at.year if nc.created_at else timezone.now().year
        key = (nc.organization_id, year)
        next_num = max_numbers.get(key, 0) + 1
        code = f"NC-{year}-{next_num:03d}"
        NoConformity.objects.using(db_alias).filter(pk=nc.pk).update(code=code)
        max_numbers[key] = next_num


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_noconformity_closed_by_noconformity_closed_date_and_more"),
    ]

    operations = [
        migrations.RunPython(populate_nc_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="noconformity",
            name="code",
            field=models.CharField(
                editable=False,
                help_text="NC-2025-001, NC-2025-002, etc.",
                max_length=20,
                unique=True,
                verbose_name="Codigo",
            ),
        ),
        migrations.AlterField(
            model_name="noconformity",
            name="origin",
            field=models.CharField(
                choices=[
                    ("INTERNAL_AUDIT", "Auditoria interna"),
                    ("EXTERNAL_AUDIT", "Auditoria externa"),
                    ("CUSTOMER", "Cliente"),
                    ("INTERNAL", "Interna"),
                    ("PRODUCTION", "Produccion"),
                    ("SUPPLIER", "Proveedor"),
                    ("OTHER", "Otro"),
                ],
                max_length=30,
                verbose_name="Origen",
            ),
        ),
    ]
