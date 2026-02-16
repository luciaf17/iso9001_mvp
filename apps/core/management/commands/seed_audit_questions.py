from django.core.management.base import BaseCommand, CommandError

from apps.core.models import Organization, AuditQuestion, Process


class Command(BaseCommand):
    help = "Seed initial audit questions for the active organization."

    def handle(self, *args, **options):
        organization = Organization.objects.filter(is_active=True).first()
        if not organization:
            organization = Organization.objects.filter(name="Metalurgica Ceibo S.R.L.").first()
        if not organization:
            raise CommandError("No se encontro una organizacion activa para seedear preguntas.")

        questions = []
        generic_questions = [
            "Existe un programa de auditorias internas vigente?",
            "Se conservan registros de auditorias previas?",
            "Se comunicaron los resultados a los responsables?",
            "Se gestionan hallazgos y acciones correctivas?",
        ]
        for index, text in enumerate(generic_questions, start=10):
            questions.append({"text": text, "process_type": None, "ordering": index})

        process_specific = {
            Process.ProcessType.STRATEGIC: [
                "Los objetivos estrategicos se revisan periodicamente?",
                "Se monitorean indicadores clave del proceso?",
            ],
            Process.ProcessType.MISSIONAL: [
                "Se ejecutan las actividades segun procedimientos definidos?",
                "Se controlan los requisitos del cliente en la operacion?",
            ],
            Process.ProcessType.SUPPORT: [
                "Los recursos necesarios estan disponibles y gestionados?",
                "Se controlan los servicios de soporte criticos?",
            ],
        }

        ordering_base = 100
        for process_type, items in process_specific.items():
            for offset, text in enumerate(items, start=1):
                questions.append({
                    "text": text,
                    "process_type": process_type,
                    "ordering": ordering_base + offset,
                })
            ordering_base += 100

        created_count = 0
        updated_count = 0
        for question in questions:
            obj, created = AuditQuestion.objects.update_or_create(
                organization=organization,
                text=question["text"],
                defaults={
                    "process_type": question["process_type"],
                    "ordering": question["ordering"],
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Preguntas creadas: {created_count} | actualizadas: {updated_count}"
            )
        )
