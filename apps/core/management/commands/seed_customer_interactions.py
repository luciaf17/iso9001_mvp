"""
Carga datos de prueba de interacciones con clientes.
Basado en el Excel R-15-01 real de Metalúrgica Ceibo.

Uso:
    python manage.py seed_customer_interactions
"""
from datetime import date
from django.core.management.base import BaseCommand
from apps.core.models import Organization, Stakeholder, CustomerInteraction


class Command(BaseCommand):
    help = "Carga interacciones con clientes de prueba basadas en datos reales de CEIBO"

    def handle(self, *args, **options):
        org = Organization.objects.filter(is_active=True).first()
        if not org:
            self.stdout.write(self.style.ERROR("No hay organización activa. Corré seed_ceibo_demo_data primero."))
            return

        # Crear stakeholders (clientes) si no existen
        clients_data = [
            ("Gauss Maquinarias", "CUSTOMER"),
            ("Agromaq Saladillo", "CUSTOMER"),
            ("Flores Pablo", "CUSTOMER"),
            ("Marcelo Delpupo", "CUSTOMER"),
            ("Fessia Maquinarias", "CUSTOMER"),
            ("Jorgelina", "COMMUNITY"),
            ("Ezequiel Arregui", "SUPPLIER"),
            ("Claudio Paulus", "COMMUNITY"),
            ("Nico Chiacchiera", "CUSTOMER"),
            ("Boyama Pinturas", "SUPPLIER"),
            ("Marcos Bustos", "CUSTOMER"),
            ("Indio Mates", "SUPPLIER"),
            ("Esteban Garcia", "CUSTOMER"),
            ("Zaion Suarez", "COMMUNITY"),
            ("Giorgis Fumigaciones", "CUSTOMER"),
            ("Tomas Tardioli", "CUSTOMER"),
            ("Luciano Benito", "SUPPLIER"),
        ]

        stakeholders = {}
        for name, stype in clients_data:
            s, created = Stakeholder.objects.get_or_create(
                organization=org,
                name=name,
                defaults={
                    "stakeholder_type": stype,
                    "expectations": "Productos de calidad y buen servicio postventa",
                },
            )
            stakeholders[name] = s
            if created:
                self.stdout.write(f"  + Stakeholder: {name} ({stype})")

        # Crear interacciones
        interactions_data = [
            {
                "date": date(2025, 12, 17),
                "customer_name": "Gauss Maquinarias",
                "project": "Pala M1000.5",
                "channel": "DEALER",
                "interaction_type": "COMPLIMENT",
                "topic": "PERFORMANCE",
                "perception": "POSITIVE",
                "impact": "HIGH",
                "requires_action": False,
                "responsible": "SALES",
                "status": "CLOSED",
                "result": "COMPLIMENT",
                "closed_date": date(2025, 12, 17),
                "observations": "Respuesta a una consulta sobre satisfaccion",
            },
            {
                "date": date(2026, 1, 26),
                "customer_name": "Agromaq Saladillo",
                "project": "Retroexcavadora",
                "channel": "DEALER",
                "interaction_type": "CLAIM",
                "topic": "PERFORMANCE",
                "perception": "NEGATIVE",
                "impact": "HIGH",
                "requires_action": True,
                "responsible": "AFTER_SALES",
                "status": "OPEN",
                "result": "CORRECTIVE_ACTION",
                "observations": "Enviar Comando Hidraulico de Repuesto",
            },
            {
                "date": date(2026, 1, 8),
                "customer_name": "Flores Pablo",
                "project": "Pala M1001",
                "channel": "WHATSAPP",
                "interaction_type": "COMPLIMENT",
                "topic": "PERFORMANCE",
                "perception": "POSITIVE",
                "impact": "HIGH",
                "requires_action": False,
                "responsible": "SALES",
                "status": "CLOSED",
                "result": "COMPLIMENT",
                "closed_date": date(2026, 1, 8),
                "observations": "Respuesta a una consulta sobre satisfaccion",
            },
            {
                "date": date(2026, 1, 14),
                "customer_name": "Flores Pablo",
                "project": "Acoplado 1 Eje",
                "channel": "WHATSAPP",
                "interaction_type": "QUERY",
                "topic": "PRICE",
                "perception": "NEUTRAL",
                "impact": "HIGH",
                "requires_action": True,
                "responsible": "SALES",
                "status": "CLOSED",
                "result": "SIMPLE_QUERY",
                "closed_date": date(2026, 1, 14),
                "observations": "Se envía Presupuesto Solicitado",
            },
            {
                "date": date(2025, 9, 29),
                "customer_name": "Marcelo Delpupo",
                "project": "Desmalezadora 2000",
                "channel": "INSTAGRAM",
                "interaction_type": "QUERY",
                "topic": "PRICE",
                "perception": "POSITIVE",
                "impact": "HIGH",
                "requires_action": True,
                "responsible": "SALES",
                "status": "CLOSED",
                "result": "SIMPLE_QUERY",
                "closed_date": date(2025, 9, 30),
                "observations": "Se contesta 3 días después de la consulta y el cliente avisa que ya compró",
            },
            {
                "date": date(2025, 10, 4),
                "customer_name": "Fessia Maquinarias",
                "project": "Acoplado 1 Eje",
                "channel": "INSTAGRAM",
                "interaction_type": "MENTION",
                "topic": "OTHER",
                "perception": "NEUTRAL",
                "impact": "HIGH",
                "requires_action": False,
                "responsible": "",
                "status": "CLOSED",
                "result": "",
                "observations": "Se etiqueta a Ceibo con un implemento terminado y se republica",
            },
            {
                "date": date(2025, 10, 12),
                "customer_name": "Jorgelina",
                "project": "Acoplado 1 Eje",
                "channel": "INSTAGRAM",
                "interaction_type": "COMPLIMENT",
                "topic": "OTHER",
                "perception": "POSITIVE",
                "impact": "HIGH",
                "requires_action": False,
                "responsible": "",
                "status": "CLOSED",
                "result": "",
                "observations": "Placa día de la Diversidad Cultural",
            },
            {
                "date": date(2025, 10, 17),
                "customer_name": "Ezequiel Arregui",
                "project": "Pala M1002",
                "channel": "INSTAGRAM",
                "interaction_type": "SUGGESTION",
                "topic": "SERVICE",
                "perception": "NEUTRAL",
                "impact": "LOW",
                "requires_action": False,
                "responsible": "",
                "status": "CLOSED",
                "result": "",
                "observations": "Se envía ideas de mejoras para implementos",
            },
            {
                "date": date(2025, 10, 16),
                "customer_name": "Claudio Paulus",
                "project": "Pala M1001",
                "channel": "INSTAGRAM",
                "interaction_type": "SUGGESTION",
                "topic": "SERVICE",
                "perception": "NEUTRAL",
                "impact": "LOW",
                "requires_action": False,
                "responsible": "",
                "status": "CLOSED",
                "result": "",
                "observations": "Se escuchan sugerencias para mejoras de producto",
            },
            {
                "date": date(2025, 10, 21),
                "customer_name": "Nico Chiacchiera",
                "project": "Pala M1001",
                "channel": "INSTAGRAM",
                "interaction_type": "QUERY",
                "topic": "PRICE",
                "perception": "NEUTRAL",
                "impact": "HIGH",
                "requires_action": True,
                "responsible": "SALES",
                "status": "OPEN",
                "result": "SIMPLE_QUERY",
                "observations": "Se debe enviar presupuesto",
            },
            {
                "date": date(2025, 11, 6),
                "customer_name": "Boyama Pinturas",
                "project": "Pala M1002",
                "channel": "INSTAGRAM",
                "interaction_type": "MENTION",
                "topic": "QUALITY",
                "perception": "POSITIVE",
                "impact": "LOW",
                "requires_action": False,
                "responsible": "",
                "status": "CLOSED",
                "result": "",
                "observations": "Se repostea reel de proveedor",
            },
            {
                "date": date(2025, 11, 12),
                "customer_name": "Marcos Bustos",
                "project": "Pala M1002",
                "channel": "INSTAGRAM",
                "interaction_type": "QUERY",
                "topic": "PRICE",
                "perception": "NEUTRAL",
                "impact": "HIGH",
                "requires_action": True,
                "responsible": "SALES",
                "status": "CLOSED",
                "result": "SIMPLE_QUERY",
                "closed_date": date(2025, 10, 22),
                "observations": "Se envía presupuesto de pala sin obtener respuesta",
            },
            {
                "date": date(2025, 11, 14),
                "customer_name": "Indio Mates",
                "project": "Acoplado 1 Eje",
                "channel": "INSTAGRAM",
                "interaction_type": "MENTION",
                "topic": "OTHER",
                "perception": "POSITIVE",
                "impact": "LOW",
                "requires_action": False,
                "responsible": "",
                "status": "CLOSED",
                "result": "",
                "observations": "Se envía foto a proveedor",
            },
            {
                "date": date(2025, 12, 1),
                "customer_name": "Esteban Garcia",
                "project": "Niveladora",
                "channel": "INSTAGRAM",
                "interaction_type": "MENTION",
                "topic": "QUALITY",
                "perception": "POSITIVE",
                "impact": "HIGH",
                "requires_action": False,
                "responsible": "",
                "status": "CLOSED",
                "result": "",
                "observations": "Se etiqueta a Ceibo con un implemento terminado y se republica",
            },
            {
                "date": date(2025, 12, 12),
                "customer_name": "Zaion Suarez",
                "project": "Tanques",
                "channel": "INSTAGRAM",
                "interaction_type": "COMPLIMENT",
                "topic": "QUALITY",
                "perception": "POSITIVE",
                "impact": "HIGH",
                "requires_action": False,
                "responsible": "",
                "status": "CLOSED",
                "result": "",
                "observations": "Se reciben felicitaciones a una historia con tanques en proceso",
            },
            {
                "date": date(2025, 12, 16),
                "customer_name": "Giorgis Fumigaciones",
                "project": "Tanques",
                "channel": "INSTAGRAM",
                "interaction_type": "QUERY",
                "topic": "PRICE",
                "perception": "NEUTRAL",
                "impact": "HIGH",
                "requires_action": True,
                "responsible": "SALES",
                "status": "OPEN",
                "result": "SIMPLE_QUERY",
                "observations": "Se debe enviar presupuesto",
            },
            {
                "date": date(2025, 12, 18),
                "customer_name": "Tomas Tardioli",
                "project": "Acoplado 1 Eje",
                "channel": "INSTAGRAM",
                "interaction_type": "MENTION",
                "topic": "QUALITY",
                "perception": "POSITIVE",
                "impact": "HIGH",
                "requires_action": False,
                "responsible": "",
                "status": "CLOSED",
                "result": "",
                "observations": "Se etiqueta a Ceibo con un implemento terminado y se republica",
            },
            {
                "date": date(2025, 12, 31),
                "customer_name": "Luciano Benito",
                "project": "Pala M1001",
                "channel": "INSTAGRAM",
                "interaction_type": "COMPLIMENT",
                "topic": "SERVICE",
                "perception": "POSITIVE",
                "impact": "HIGH",
                "requires_action": False,
                "responsible": "",
                "status": "CLOSED",
                "result": "",
                "observations": "Saludos para año nuevo",
            },
        ]

        created_count = 0
        for data in interactions_data:
            customer_name = data.pop("customer_name")
            customer = stakeholders.get(customer_name)

            interaction, created = CustomerInteraction.objects.get_or_create(
                organization=org,
                date=data["date"],
                customer=customer,
                interaction_type=data["interaction_type"],
                observations=data.get("observations", ""),
                defaults={
                    "customer_name": customer_name if not customer else "",
                    **data,
                },
            )

            if created:
                created_count += 1
                self.stdout.write(f"  + {interaction.code}: {customer_name} - {data['interaction_type']}")

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Seed completado: {created_count} interacciones creadas"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"   Total stakeholders: {len(stakeholders)}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"\n   Para probar el informe de satisfacción:"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"   Período sugerido: 01/09/2025 al 31/01/2026"
        ))