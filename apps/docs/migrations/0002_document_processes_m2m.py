from django.db import migrations, models


def copy_process_to_processes(apps, schema_editor):
    Document = apps.get_model("docs", "Document")
    for doc in Document.objects.exclude(process_id__isnull=True):
        doc.processes.add(doc.process_id)


class Migration(migrations.Migration):

    dependencies = [
        ("docs", "0001_initial"),
        ("core", "0006_organizationcontext_documents"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="processes",
            field=models.ManyToManyField(
                blank=True,
                related_name="documents",
                to="core.process",
                verbose_name="Procesos",
            ),
        ),
        migrations.RunPython(copy_process_to_processes, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="document",
            name="process",
        ),
    ]
