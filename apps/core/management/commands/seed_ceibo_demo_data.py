"""
Seed de datos de ejemplo para Metalúrgica Ceibo S.R.L.
Basado en documentación ISO real de la empresa.

Ejecutar:
  python manage.py seed_ceibo_process_map   (primero, si no se ejecutó)
  python manage.py seed_audit_questions     (segundo)
  python manage.py seed_ceibo_demo_data     (este comando)

Crea: usuarios, contexto, stakeholders, riesgos, documentos, NCs, CAPAs,
objetivos, indicadores, proveedores, empleados, competencias, capacitaciones,
auditoría interna, revisión por la dirección, productos no conformes.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.core.models import (
    Organization, Site, Process, Stakeholder, RiskOpportunity,
    OrganizationContext, NoConformity, CAPAAction, QualityObjective,
    InternalAudit, AuditQuestion, AuditAnswer, AuditFinding,
    ManagementReview, QualityIndicator, IndicatorMeasurement,
    NonconformingOutput, Supplier, SupplierEvaluation,
    Employee, Competency, EmployeeCompetency, Training, TrainingAttendance,
)
from apps.docs.models import Document, DocumentVersion

User = get_user_model()


class Command(BaseCommand):
    help = "Carga datos de ejemplo realistas para Metalúrgica Ceibo S.R.L."

    def handle(self, *args, **options):
        with transaction.atomic():
            self._seed_all()
        self.stdout.write(self.style.SUCCESS(
            "\n✅ Datos de ejemplo cargados exitosamente."
            "\n\nUsuarios creados (password: ceibo2026):"
            "\n  jlambertucci (Socia Gerente - Admin)"
            "\n  earregui (Ingeniería de Producto - Calidad)"
            "\n  cgarcia (Supervisor de Producción)"
            "\n  mfernandez (Responsable de Compras)"
            "\n  lsosa (Operario Senior)"
        ))

    def _seed_all(self):
        today = date.today()

        # ===== ORGANIZACIÓN Y SEDE =====
        org, _ = Organization.objects.update_or_create(
            name="Metalurgica Ceibo S.R.L.",
            defaults={"is_active": True}
        )
        site, _ = Site.objects.update_or_create(
            organization=org, name="Planta Armstrong",
            defaults={"is_active": True}
        )
        self.stdout.write("  Organización y sede: OK")

        # ===== USUARIOS =====
        calidad_group, _ = Group.objects.get_or_create(name="Calidad")
        admin_group, _ = Group.objects.get_or_create(name="Admin")

        users = {}
        user_data = [
            ("jlambertucci", "Julieta", "Lambertucci", "jlambertucci@ceibo.com",
             [admin_group, calidad_group]),
            ("earregui", "Ezequiel", "Arregui", "earregui@ceibo.com",
             [calidad_group]),
            ("cgarcia", "Carlos", "García", "cgarcia@ceibo.com", []),
            ("mfernandez", "Marcela", "Fernández", "mfernandez@ceibo.com", []),
            ("lsosa", "Lucas", "Sosa", "lsosa@ceibo.com", []),
        ]
        for username, first, last, email, groups in user_data:
            u, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first, "last_name": last,
                    "email": email, "is_active": True,
                }
            )
            if created:
                u.set_password("ceibo2026")
                u.save()
            for g in groups:
                u.groups.add(g)
            users[username] = u
        self.stdout.write(f"  Usuarios: {len(users)}")

        # ===== PROCESOS (deben existir del seed_ceibo_process_map) =====
        processes = {p.code: p for p in Process.objects.filter(organization=org)}
        if not processes:
            self.stdout.write(self.style.WARNING(
                "  ⚠️ No hay procesos. Ejecutá primero: python manage.py seed_ceibo_process_map"
            ))
        self.stdout.write(f"  Procesos existentes: {len(processes)}")

        # ===== CONTEXTO DE LA ORGANIZACIÓN =====
        OrganizationContext.objects.update_or_create(
            organization=org,
            defaults={
                "site": site,
                "owner": users["jlambertucci"],
                "review_date": date(2026, 1, 15),
                "summary": (
                    "Metalúrgica Ceibo S.R.L. se dedica a la fabricación de implementos "
                    "agrícolas. Con sede en Armstrong, Santa Fe, Argentina (Área Industrial "
                    "lote 42J). Más de 20 años en el mercado (fundada en 2000).\n\n"
                    "Productos principales: palas frontales acoplables a todo tipo de tractores "
                    "(producto principal en ventas), retroexcavadoras, volcadores, grúas de "
                    "arrastre para manejo de bolsones big-bag, niveladoras de arrastre, "
                    "desmalezadoras, tanques para combustible (con certificado de homologación "
                    "UNR), acoplados playos, carro elevador y volcador para asistencia de "
                    "cosecha en viñedos.\n\n"
                    "Contexto externo: competencia desde talleres informales hasta fábricas de "
                    "+50 empleados. Diferenciación por calidad y diversificación de productos. "
                    "Oportunidad: obtener LCM (Licencias de Configuración de Modelo) vía INTI "
                    "para patentamiento de chasis.\n\n"
                    "Contexto interno: equipo técnico experimentado, planta ampliada, "
                    "implementación 5S completada, procesos de soldadura como core competency."
                ),
                "qms_scope": (
                    "Diseño, fabricación y comercialización de palas frontales, grúas de "
                    "arrastre, niveladoras de arrastre, desmalezadoras y tanques para "
                    "combustible, volcadores, retroexcavadoras y acoplados.\n\n"
                    "Aplica a todo el personal en Área Industrial lote 42J, Armstrong, "
                    "Santa Fe, Argentina. Exceptuando procesos tercerizados en Cabina de Pintura.\n\n"
                    "Norma aplicable: ISO 9001:2015."
                ),
            }
        )
        self.stdout.write("  Contexto de la organización: OK")

        # ===== STAKEHOLDERS (datos reales del FP-00) =====
        stakeholders_data = [
            ("Clientes", "CUSTOMER",
             "Entrega en tiempo y forma de los equipos comprados, calidad de acuerdo "
             "a lo ofrecido. Planos y especificaciones de acuerdo a lo pactado en la venta."),
            ("Proveedores", "SUPPLIER",
             "Pagos en término. Cumplir el programa de compras acordado."),
            ("Empleados", "EMPLOYEE",
             "Cumplimiento de obligaciones pactadas en acuerdos laborales individuales y "
             "colectivos. Buen ambiente de trabajo y mejora continua de las condiciones laborales."),
            ("Socios", "OWNER",
             "Mejora continua del clima laboral, económico y operativo. Conformidad de los "
             "trabajadores. Rentabilidad y crecimiento. Transparencia."),
            ("Comunidad de Armstrong", "COMMUNITY",
             "Generar puestos de trabajo, realizar aportes de carácter social, apoyar "
             "oportunidades de formación, colaborar con el cuidado del medio ambiente."),
            ("Administraciones Públicas", "REGULATORY",
             "Municipalidad: habilitación municipal vigente. Ministerio del Trabajo de Santa Fe: "
             "cumplimiento Ley de Higiene y Seguridad. ARCA: obligaciones fiscales en tiempo y forma."),
            ("Secretaría de Industria / INTI", "REGULATORY",
             "Cumplir requisitos legales y técnicos para Licencias de Configuración de Modelo (LCM). "
             "Certificación ISO 9001 como prerequisito."),
            ("Asesores (contador, abogado, SHyS)", "SUPPLIER",
             "Cumplir con la entrega a tiempo y correcta de la información requerida."),
        ]
        for name, stype, expectations in stakeholders_data:
            Stakeholder.objects.update_or_create(
                organization=org, name=name,
                defaults={
                    "site": site, "stakeholder_type": stype,
                    "expectations": expectations,
                    "review_date": date(2026, 1, 15), "is_active": True,
                }
            )
        self.stdout.write(f"  Stakeholders: {len(stakeholders_data)}")

        # ===== RIESGOS Y OPORTUNIDADES =====
        p09 = processes.get("09")
        p08 = processes.get("08")
        p07 = processes.get("07")
        p10 = processes.get("10")
        p12 = processes.get("12")
        p13 = processes.get("13")

        risks_data = [
            ("Demora en entrega de acero y materias primas", "RISK", p08, 4, 4,
             "OPEN", users["mfernandez"],
             "Diversificar proveedores de chapa. Stock de seguridad de 30 días para materiales críticos."),
            ("Defectos en soldadura por falta de capacitación", "RISK", p09, 3, 4,
             "IN_PROGRESS", users["cgarcia"],
             "Plan de capacitación semestral en soldadura MIG/MAG. Certificación de soldadores según IT-09-02."),
            ("Accidente laboral en sector corte pantógrafo", "RISK", p09, 2, 5,
             "IN_PROGRESS", users["cgarcia"],
             "Capacitación en seguridad según plan de formación R-12-05. EPP obligatorio. "
             "Mantenimiento preventivo de equipos."),
            ("Pérdida de clientes por incumplimiento de plazos de entrega", "RISK", p07, 3, 4,
             "OPEN", users["jlambertucci"],
             "Implementar seguimiento semanal de órdenes de fabricación. Reuniones de producción."),
            ("Falta de personal calificado en soldadura", "RISK", p12, 3, 3,
             "OPEN", users["earregui"],
             "Programa de formación interna. Convenio con escuela técnica de Armstrong."),
            ("Rotura de equipos críticos (pantógrafo, puente grúa)", "RISK", p13, 2, 5,
             "IN_PROGRESS", users["cgarcia"],
             "Plan de mantenimiento preventivo. Stock de repuestos críticos."),
            ("Obtención de LCM para patentamiento de chasis", "OPPORTUNITY", p10, 3, 5,
             "OPEN", users["jlambertucci"],
             "Completar ensayos INTI. Certificación ISO 9001 como prerequisito. "
             "Habilita nuevo mercado de acoplados y tanques patentables."),
            ("Expansión línea de productos vitivinícolas", "OPPORTUNITY", p07, 3, 3,
             "OPEN", users["jlambertucci"],
             "Carro elevador y volcador para viñedos ahorra 50% mano de obra. "
             "Potencial en región de Cuyo y Mendoza."),
        ]
        for title, kind, process, prob, impact, status, owner, plan in risks_data:
            RiskOpportunity.objects.update_or_create(
                organization=org, title=title,
                defaults={
                    "site": site, "related_process": process,
                    "description": title, "kind": kind,
                    "probability": prob, "impact": impact,
                    "treatment_plan": plan, "owner": owner,
                    "due_date": date(2026, 6, 30), "status": status,
                    "is_active": True,
                }
            )
        self.stdout.write(f"  Riesgos/Oportunidades: {len(risks_data)}")

        # ===== DOCUMENTOS (basados en documentación real) =====
        docs_data = [
            ("MSGC-16-01", "Manual de Calidad", "MANUAL", []),
            ("R-00-01", "Política de Calidad", "FORMAT", ["00"]),
            ("R-00-02", "Mapa de Procesos", "FORMAT", ["00"]),
            ("R-00-03", "Organigrama Metalúrgica Ceibo", "FORMAT", ["00"]),
            ("R-00-04", "Matriz de Requisitos Legales Aplicables", "FORMAT", ["00"]),
            ("FP-00", "Contexto de la Organización", "PROCEDURE", ["00"]),
            ("FP-01", "Información Documentada", "PROCEDURE", ["01"]),
            ("FP-02", "Planificación y Gestión del Cambio", "PROCEDURE", ["02"]),
            ("FP-03", "Gestión de Riesgos y Oportunidades", "PROCEDURE", ["03"]),
            ("FP-04", "Auditoría", "PROCEDURE", ["04"]),
            ("FP-05", "No Conformidades", "PROCEDURE", ["05"]),
            ("FP-06", "Seguimiento y Medición", "PROCEDURE", ["06"]),
            ("FP-07", "Gestión de Ventas y Comercialización", "PROCEDURE", ["07"]),
            ("FP-08", "Gestión de Compras", "PROCEDURE", ["08"]),
            ("FP-09", "Planificación y Ejecución de la Producción", "PROCEDURE", ["09"]),
            ("FP-10", "Diseño y Desarrollo", "PROCEDURE", ["10"]),
            ("FP-11", "Gestión de Post Venta", "PROCEDURE", ["11"]),
            ("FP-12", "Gestión de Recursos Humanos", "PROCEDURE", ["12"]),
            ("FP-13", "Gestión de la Infraestructura y Mantenimiento", "PROCEDURE", ["13"]),
            ("FP-14", "Comunicación, Consulta y Divulgación", "PROCEDURE", ["14"]),
            ("FP-15", "Satisfacción del Cliente", "PROCEDURE", ["15"]),
            ("IT-03-00-00-01", "Análisis y Evaluación del Riesgo", "INSTRUCTION", ["03"]),
            ("IT-09-00-00-01", "Instructivo Encargado de Planta", "INSTRUCTION", ["09"]),
            ("IT-09-01-00-01", "Instructivo Sector EIMP", "INSTRUCTION", ["09"]),
            ("IT-09-01-01-01", "Instructivo Operario Corte Pantógrafo", "INSTRUCTION", ["09"]),
            ("IT-09-02-00-01", "Instructivo Sector Soldadura", "INSTRUCTION", ["09"]),
            ("IT-09-02-00-02", "Procedimientos Soldadura Tipo 001", "INSTRUCTION", ["09"]),
            ("IT-09-02-06-01", "Soldado Chasis Palas Frontales", "INSTRUCTION", ["09"]),
            ("IT-09-02-07-01", "Soldado de Cucharas Palas Frontales", "INSTRUCTION", ["09"]),
            ("IT-09-02-08-01", "Soldado Retroexcavadoras", "INSTRUCTION", ["09"]),
            ("IT-09-02-08-02", "Soldado Volcadores", "INSTRUCTION", ["09"]),
            ("IT-09-02-09-01", "Soldado Grúas de Arrastre", "INSTRUCTION", ["09"]),
            ("IT-09-02-10-01", "Soldado Tanques para Combustible", "INSTRUCTION", ["09"]),
            ("IT-09-03-00-01", "Instructivo Sector Limpieza y Pintura", "INSTRUCTION", ["09"]),
            ("IT-09-04-00-01", "Instructivo Sector Armado Final", "INSTRUCTION", ["09"]),
            ("IT-09-04-00-02", "Prueba Hidráulica Pre Entrega", "INSTRUCTION", ["09"]),
            ("IT-09-05-00-01", "Instructivo Sector Liberación y Entrega", "INSTRUCTION", ["09"]),
            ("R-05-01", "Registro No Conformidades", "FORMAT", ["05"]),
            ("R-07-01", "Despacho de Mercadería", "FORMAT", ["07"]),
            ("R-08-01", "Evaluación de Proveedores", "FORMAT", ["08"]),
            ("R-10-01", "Control de Cambios de Ingeniería", "FORMAT", ["10"]),
            ("R-12-01", "Ficha de Personal", "FORMAT", ["12"]),
            ("R-12-02", "Registro de Formación", "FORMAT", ["12"]),
            ("R-12-03", "Competencias, Funciones y Responsabilidades", "FORMAT", ["12"]),
            ("R-14-01", "Plan de Comunicación", "FORMAT", ["14"]),
            ("R-16-01", "Acta de Revisión del Sistema", "FORMAT", ["16"]),
        ]
        for code, title, dtype, proc_codes in docs_data:
            doc, _ = Document.objects.update_or_create(
                code=code,
                defaults={
                    "title": title, "doc_type": dtype,
                    "owner": users["earregui"], "is_active": True,
                }
            )
            if proc_codes:
                procs = Process.objects.filter(organization=org, code__in=proc_codes)
                doc.processes.set(procs)
            if not doc.versions.exists():
                DocumentVersion.objects.create(
                    document=doc, version_number="1.0",
                    file="documents/placeholder.pdf",
                    effective_date=date(2025, 6, 1),
                    review_due_date=date(2026, 6, 1),
                    status="APPROVED",
                    created_by=users["earregui"],
                    notes="Versión inicial aprobada.",
                )
        self.stdout.write(f"  Documentos: {len(docs_data)}")

        # ===== NO CONFORMIDADES =====
        nc1, _ = NoConformity.objects.update_or_create(
            organization=org,
            title="Soldadura con porosidad en pala frontal lote PF-2026-015",
            defaults={
                "site": site, "related_process": p09,
                "description": (
                    "Se detectaron cordones de soldadura con porosidad en 3 unidades de "
                    "pala frontal durante inspección en sector Armado Final (IT-09-04). "
                    "Lote: PF-2026-015. Afecta zona de unión cuchilla-cuerpo principal en "
                    "estación S1 (Soldado Chasis Palas Frontales)."
                ),
                "origin": "PRODUCTION", "severity": "MAJOR",
                "detected_at": today - timedelta(days=12),
                "detected_by": users["cgarcia"],
                "owner": users["earregui"],
                "due_date": today + timedelta(days=18),
                "status": "IN_TREATMENT",
                "root_cause_analysis": (
                    "Análisis 5 Por Qués:\n"
                    "1. ¿Por qué porosidad? → Gas de protección insuficiente\n"
                    "2. ¿Por qué gas insuficiente? → Regulador de flujo defectuoso en estación S1\n"
                    "3. ¿Por qué no se detectó antes? → No hay verificación pre-operacional del equipo\n"
                    "4. ¿Por qué no hay verificación? → No está incluida en IT-09-02-06-01\n"
                    "5. ¿Por qué no está incluida? → Instructivo no actualizado desde versión original\n\n"
                    "Causa raíz: Falta de mantenimiento preventivo de equipos de soldadura y "
                    "ausencia de check pre-operacional en instructivo de soldado de chasis."
                ),
                "corrective_action": (
                    "1. Actualizar IT-09-02-06-01 incluyendo checklist pre-operacional de equipos\n"
                    "2. Reemplazar reguladores de gas en estaciones S1 a S6\n"
                    "3. Capacitar operarios soldadores en verificación de parámetros\n"
                    "4. Agregar punto de control en inspección intermedia post-soldadura"
                ),
            }
        )

        nc2, _ = NoConformity.objects.update_or_create(
            organization=org,
            title="Entrega fuera de plazo - pedido retroexcavadoras RE-200",
            defaults={
                "site": site, "related_process": p07,
                "description": (
                    "Pedido #2026-0087 de 3 retroexcavadoras RE-200 para cliente de Córdoba "
                    "entregado con 12 días de demora. Causa inmediata: falta de material "
                    "(cilindros hidráulicos) por demora del proveedor."
                ),
                "origin": "CUSTOMER", "severity": "MAJOR",
                "detected_at": today - timedelta(days=25),
                "detected_by": users["jlambertucci"],
                "owner": users["mfernandez"],
                "due_date": today + timedelta(days=5),
                "status": "IN_ANALYSIS",
                "root_cause_analysis": "",
                "corrective_action": "",
            }
        )

        nc3, _ = NoConformity.objects.update_or_create(
            organization=org,
            title="Dimensiones fuera de tolerancia en corte pantógrafo",
            defaults={
                "site": site, "related_process": p09,
                "description": (
                    "Piezas cortadas en pantógrafo para grúa de arrastre GA-150 con desviación "
                    "de +3mm respecto al plano. Detectado por operario de soldadura al intentar "
                    "ensamblar. 15 piezas afectadas."
                ),
                "origin": "INTERNAL", "severity": "MINOR",
                "detected_at": today - timedelta(days=5),
                "detected_by": users["lsosa"],
                "owner": users["cgarcia"],
                "due_date": today + timedelta(days=25),
                "status": "OPEN",
                "root_cause_analysis": "",
                "corrective_action": "",
            }
        )

        nc4, _ = NoConformity.objects.update_or_create(
            organization=org,
            title="Instructivo de pintura desactualizado - IT-09-03-13-01",
            defaults={
                "site": site, "related_process": p09,
                "description": (
                    "Durante auditoría interna se detectó que el instructivo de pintura "
                    "IT-09-03-13-01 no refleja el cambio de marca de pintura realizado hace "
                    "3 meses. El operario usa proporciones de mezcla diferentes a las documentadas."
                ),
                "origin": "INTERNAL_AUDIT", "severity": "MINOR",
                "detected_at": today - timedelta(days=40),
                "detected_by": users["earregui"],
                "owner": users["earregui"],
                "due_date": today - timedelta(days=10),
                "status": "CLOSED",
                "root_cause_analysis": (
                    "El cambio de proveedor de pintura se realizó sin seguir el proceso de "
                    "gestión del cambio (FP-02). No se actualizó la documentación."
                ),
                "corrective_action": (
                    "1. Actualizar IT-09-03-13-01 con nueva marca y proporciones\n"
                    "2. Recordar a responsables de compras que cambios de insumos críticos "
                    "deben seguir FP-02"
                ),
                "verification_date": today - timedelta(days=5),
                "is_effective": True,
                "verification_notes": "Instructivo actualizado y distribuido. Operario confirma uso correcto.",
                "closed_date": today - timedelta(days=3),
                "closed_by": users["earregui"],
            }
        )
        self.stdout.write("  No Conformidades: 4")

        # ===== ACCIONES CAPA =====
        CAPAAction.objects.update_or_create(
            organization=org,
            no_conformity=nc1,
            title="Reemplazar reguladores de gas estaciones S1-S6",
            defaults={
                "description": "Comprar y reemplazar reguladores de flujo de gas en las 6 estaciones de soldadura.",
                "action_type": "CORRECTIVE", "owner": users["cgarcia"],
                "due_date": today + timedelta(days=7), "status": "IN_PROGRESS",
            }
        )
        CAPAAction.objects.update_or_create(
            organization=org,
            no_conformity=nc1,
            title="Actualizar IT-09-02-06-01 con checklist pre-operacional",
            defaults={
                "description": "Incluir verificación de gas, voltaje, velocidad de alimentación antes de iniciar soldadura.",
                "action_type": "CORRECTIVE", "owner": users["earregui"],
                "due_date": today + timedelta(days=14), "status": "OPEN",
            }
        )
        CAPAAction.objects.update_or_create(
            organization=org,
            no_conformity=nc1,
            title="Capacitación en verificación de parámetros de soldadura",
            defaults={
                "description": "Capacitar a todos los operarios de soldadura en el nuevo checklist pre-operacional.",
                "action_type": "PREVENTIVE", "owner": users["cgarcia"],
                "due_date": today + timedelta(days=21), "status": "OPEN",
            }
        )
        CAPAAction.objects.update_or_create(
            organization=org,
            no_conformity=nc4,
            title="Actualizar instructivo de pintura IT-09-03-13-01",
            defaults={
                "description": "Actualizar proporciones de mezcla según nueva marca de pintura.",
                "action_type": "CORRECTIVE", "owner": users["earregui"],
                "due_date": today - timedelta(days=15), "status": "DONE",
                "completed_at": timezone.now() - timedelta(days=8),
                "completion_notes": "Instructivo actualizado, aprobado por Julieta Lambertucci, distribuido a operarios.",
            }
        )
        self.stdout.write("  Acciones CAPA: 4")

        # ===== OBJETIVOS DE CALIDAD =====
        objectives_data = [
            ("Reducir NCs de soldadura en 50%", "Cantidad de NCs originadas en soldadura",
             p09, 6, 2, "MONTHLY", users["cgarcia"]),
            ("Cumplir plazos de entrega al 95%", "% de pedidos entregados en fecha",
             p07, Decimal("95.00"), Decimal("88.50"), "MONTHLY", users["jlambertucci"]),
            ("Completar plan de capacitación anual", "% de capacitaciones ejecutadas vs planificadas",
             p12, Decimal("100.00"), Decimal("60.00"), "QUARTERLY", users["earregui"]),
            ("Mantener tasa de productos no conformes < 2%", "% de PNC sobre producción total",
             p09, Decimal("2.00"), Decimal("1.80"), "MONTHLY", users["cgarcia"]),
        ]
        for title, indicator, process, target, current, freq, owner in objectives_data:
            QualityObjective.objects.update_or_create(
                organization=org, title=title,
                defaults={
                    "site": site, "related_process": process,
                    "description": title, "indicator": indicator,
                    "target_value": target, "current_value": current,
                    "unit": "%" if "%" in indicator else "cantidad",
                    "frequency": freq, "owner": owner,
                    "start_date": date(2026, 1, 1),
                    "due_date": date(2026, 12, 31),
                    "is_active": True,
                }
            )
        self.stdout.write(f"  Objetivos de calidad: {len(objectives_data)}")

        # ===== INDICADORES =====
        indicators_data = [
            ("Tasa de productos no conformes", "% de PNC sobre unidades producidas",
             p09, "MONTHLY", Decimal("2.00"), "LESS_EQUAL", "%"),
            ("Cumplimiento de entregas", "% de pedidos entregados en fecha comprometida",
             p07, "MONTHLY", Decimal("95.00"), "GREATER_EQUAL", "%"),
            ("Índice de satisfacción del cliente", "Puntuación promedio encuestas de satisfacción",
             None, "QUARTERLY", Decimal("4.00"), "GREATER_EQUAL", "puntos (1-5)"),
            ("Eficacia de capacitaciones", "% de capacitaciones evaluadas como eficaces",
             p12, "QUARTERLY", Decimal("80.00"), "GREATER_EQUAL", "%"),
            ("Tasa de rechazo en recepción de materiales", "% de lotes rechazados sobre total recibido",
             p08, "MONTHLY", Decimal("5.00"), "LESS_EQUAL", "%"),
        ]
        for name, desc, process, freq, target, comp, unit in indicators_data:
            indicator, _ = QualityIndicator.objects.update_or_create(
                organization=org, name=name,
                defaults={
                    "description": desc, "related_process": process,
                    "frequency": freq, "target_value": target,
                    "comparison_type": comp, "unit": unit, "is_active": True,
                }
            )
            # Agregar mediciones de ejemplo (últimos 3 meses)
            if not indicator.measurements.exists():
                sample_values = {
                    "Tasa de productos no conformes": [Decimal("1.5"), Decimal("2.1"), Decimal("1.8")],
                    "Cumplimiento de entregas": [Decimal("91.0"), Decimal("87.0"), Decimal("93.0")],
                    "Índice de satisfacción del cliente": [Decimal("4.2")],
                    "Eficacia de capacitaciones": [Decimal("75.0")],
                    "Tasa de rechazo en recepción de materiales": [Decimal("3.0"), Decimal("4.5"), Decimal("2.8")],
                }
                for i, val in enumerate(sample_values.get(name, [])):
                    IndicatorMeasurement.objects.create(
                        indicator=indicator,
                        measurement_date=today - timedelta(days=30 * (len(sample_values.get(name, [])) - i)),
                        value=val, notes="Medición cargada automáticamente.",
                    )
        self.stdout.write(f"  Indicadores: {len(indicators_data)}")

        # ===== PROVEEDORES =====
        suppliers_data = [
            ("Aceros Gerdau", "RAW_MATERIAL", "30-12345678-9", "APPROVED"),
            ("Hidráulica San Lorenzo", "SERVICE", "30-98765432-1", "APPROVED"),
            ("Pinturería Industrial Rosario", "RAW_MATERIAL", "30-55667788-0", "CONDITIONAL"),
            ("Transporte Andreani", "SERVICE", "30-11223344-5", "APPROVED"),
            ("Metalúrgica del Litoral", "OUTSOURCED_PROCESS", "30-44556677-8", "PENDING"),
        ]
        for name, category, cuit, status in suppliers_data:
            supplier, _ = Supplier.objects.update_or_create(
                organization=org, name=name,
                defaults={
                    "site": site, "category": category, "cuit": cuit,
                    "status": status, "is_active": True,
                    "next_evaluation_date": date(2026, 7, 1),
                }
            )
            if status == "APPROVED" and not supplier.evaluations.exists():
                SupplierEvaluation.objects.create(
                    supplier=supplier, organization=org,
                    evaluation_date=today - timedelta(days=60),
                    evaluator=users["mfernandez"],
                    quality_score=4, delivery_score=4, price_score=3,
                    decision="APPROVED",
                    notes="Evaluación periódica. Cumple estándares de calidad.",
                )
        self.stdout.write(f"  Proveedores: {len(suppliers_data)}")

        # ===== EMPLEADOS Y COMPETENCIAS =====
        employees_data = [
            ("Carlos", "García", "Supervisor de Producción", "Producción"),
            ("Lucas", "Sosa", "Operario Soldador Senior", "Soldadura"),
            ("Martín", "Aguirre", "Operario Corte Pantógrafo", "EIMP"),
            ("Diego", "Peralta", "Operario Soldador", "Soldadura"),
            ("Pablo", "Ramírez", "Operario Pintura", "Limpieza y Pintura"),
            ("Facundo", "Torres", "Operario Armado Final", "Armado Final"),
            ("Gustavo", "Medina", "Encargado de Planta", "Producción"),
        ]
        employees = {}
        for first, last, position, dept in employees_data:
            emp, _ = Employee.objects.update_or_create(
                organization=org, email=f"{first.lower()}.{last.lower()}@ceibo.com",
                defaults={
                    "first_name": first, "last_name": last,
                    "position": position, "department": dept,
                    "is_active": True,
                }
            )
            employees[f"{first} {last}"] = emp

        # Competencias
        competencies_data = [
            ("Soldadura MIG/MAG", "Operario Soldador"),
            ("Soldadura MIG/MAG", "Operario Soldador Senior"),
            ("Lectura de planos técnicos", "Operario Soldador"),
            ("Lectura de planos técnicos", "Operario Corte Pantógrafo"),
            ("Operación de pantógrafo CNC", "Operario Corte Pantógrafo"),
            ("Seguridad e higiene industrial", "Operario Soldador"),
            ("Seguridad e higiene industrial", "Operario Corte Pantógrafo"),
            ("Pintura industrial", "Operario Pintura"),
            ("Prueba hidráulica", "Operario Armado Final"),
            ("Gestión de producción", "Supervisor de Producción"),
        ]
        for comp_name, position in competencies_data:
            comp, _ = Competency.objects.update_or_create(
                organization=org, name=comp_name, required_for_position=position,
                defaults={"description": f"Competencia: {comp_name} para puesto {position}"}
            )

        # Asignar competencias a empleados
        assignments = [
            ("Lucas Sosa", "Soldadura MIG/MAG", "Operario Soldador Senior", 4, 4),
            ("Diego Peralta", "Soldadura MIG/MAG", "Operario Soldador", 4, 3),
            ("Martín Aguirre", "Operación de pantógrafo CNC", "Operario Corte Pantógrafo", 4, 4),
            ("Diego Peralta", "Lectura de planos técnicos", "Operario Soldador", 3, 2),
            ("Pablo Ramírez", "Pintura industrial", "Operario Pintura", 4, 3),
        ]
        for emp_name, comp_name, position, required, current in assignments:
            emp = employees.get(emp_name)
            comp = Competency.objects.filter(
                organization=org, name=comp_name, required_for_position=position
            ).first()
            if emp and comp:
                EmployeeCompetency.objects.update_or_create(
                    employee=emp, competency=comp,
                    defaults={
                        "level_required": required, "level_current": current,
                        "last_evaluated": today - timedelta(days=30),
                    }
                )
        self.stdout.write(f"  Empleados: {len(employees_data)}, Competencias: {len(competencies_data)}")

        # ===== CAPACITACIONES =====
        training1, _ = Training.objects.update_or_create(
            organization=org, title="Soldadura MIG/MAG - Nivel Avanzado",
            defaults={
                "description": "Capacitación en técnicas avanzadas de soldadura MIG/MAG para implementos agrícolas.",
                "provider": "Centro de Formación Industrial Armstrong",
                "training_date": today - timedelta(days=20),
                "evidence_file": "",
            }
        )
        training2, _ = Training.objects.update_or_create(
            organization=org, title="Seguridad e Higiene - Actualización anual",
            defaults={
                "description": "Capacitación obligatoria anual en seguridad e higiene industrial.",
                "provider": "ART Prevención",
                "training_date": today - timedelta(days=45),
            }
        )
        # Asistencias
        for emp_name in ["Lucas Sosa", "Diego Peralta"]:
            emp = employees.get(emp_name)
            if emp:
                TrainingAttendance.objects.update_or_create(
                    training=training1, employee=emp,
                    defaults={"completion_status": "COMPLETED"}
                )
        for emp in employees.values():
            TrainingAttendance.objects.update_or_create(
                training=training2, employee=emp,
                defaults={"completion_status": "COMPLETED"}
            )
        self.stdout.write("  Capacitaciones: 2")

        # ===== PRODUCTO NO CONFORME =====
        NonconformingOutput.objects.update_or_create(
            organization=org,
            product_or_service="Pala Frontal PF-300 - Lote PF-2026-015",
            detected_at=today - timedelta(days=12),
            defaults={
                "site": site, "related_process": p09,
                "description": "3 unidades con cordones de soldadura porosos en unión cuchilla-cuerpo.",
                "quantity": Decimal("3"), "severity": "MAJOR",
                "disposition": "REWORK",
                "disposition_notes": "Reparar soldadura en las 3 unidades. Re-inspeccionar antes de liberar.",
                "responsible": users["cgarcia"],
                "detected_by": users["cgarcia"],
                "status": "IN_TREATMENT",
                "linked_nc": nc1,
            }
        )
        NonconformingOutput.objects.update_or_create(
            organization=org,
            product_or_service="Grúa de Arrastre GA-150 - piezas corte pantógrafo",
            detected_at=today - timedelta(days=5),
            defaults={
                "site": site, "related_process": p09,
                "description": "15 piezas con desviación +3mm. No ensamblan correctamente.",
                "quantity": Decimal("15"), "severity": "MINOR",
                "disposition": "SCRAP",
                "disposition_notes": "Descartar piezas fuera de tolerancia. Cortar nuevas con parámetros corregidos.",
                "responsible": users["cgarcia"],
                "detected_by": users["lsosa"],
                "status": "CLOSED",
                "closed_at": today - timedelta(days=3),
                "linked_nc": nc3,
            }
        )
        self.stdout.write("  Productos no conformes: 2")

        # ===== AUDITORÍA INTERNA =====
        audit, _ = InternalAudit.objects.update_or_create(
            organization=org,
            title="Auditoría Interna Q1 2026 - Producción y Documentación",
            defaults={
                "site": site,
                "audit_date": today - timedelta(days=45),
                "audit_type": "INTERNAL",
                "auditor": users["earregui"],
                "auditee": "Carlos García - Supervisor de Producción",
                "scope": (
                    "Verificar conformidad del proceso de producción (FP-09) y control "
                    "documental (FP-01) con los requisitos de ISO 9001:2015. "
                    "Procesos 09 (Producción) y 01 (Información Documentada)."
                ),
                "status": "COMPLETED",
            }
        )
        if p09:
            audit.related_processes.add(p09)
        p01 = processes.get("01")
        if p01:
            audit.related_processes.add(p01)

        # Hallazgos de la auditoría
        AuditFinding.objects.update_or_create(
            audit=audit,
            description="Instructivo de pintura IT-09-03-13-01 no actualizado tras cambio de proveedor de pintura.",
            defaults={
                "related_process": p09,
                "finding_type": "NONCONFORMITY",
                "severity": "MINOR",
                "nc": nc4,
            }
        )
        AuditFinding.objects.update_or_create(
            audit=audit,
            description=(
                "Oportunidad de mejora: implementar checklist de verificación pre-operacional "
                "en estaciones de soldadura para prevenir defectos."
            ),
            defaults={
                "related_process": p09,
                "finding_type": "IMPROVEMENT_OPPORTUNITY",
                "severity": None,
            }
        )
        self.stdout.write("  Auditoría interna: 1 (con 2 hallazgos)")

        # ===== REVISIÓN POR LA DIRECCIÓN =====
        ManagementReview.objects.update_or_create(
            organization=org,
            review_date=date(2026, 1, 15),
            defaults={
                "chairperson": users["jlambertucci"],
                "attendees": "Julieta Lambertucci (Socia Gerente), Ezequiel Arregui (Ing. de Producto), Carlos García (Sup. Producción)",
                "audit_results_summary": (
                    "Auditoría interna Q4 2025 completada. 1 NC menor (documentación) y "
                    "1 oportunidad de mejora (control de soldadura). Hallazgos gestionados."
                ),
                "customer_feedback_summary": (
                    "Satisfacción general positiva (4.2/5). Reclamo por demora en entrega "
                    "de retroexcavadoras. Se está gestionando como NC."
                ),
                "process_performance_summary": (
                    "Producción cumplió 88.5% de entregas a tiempo (meta: 95%). "
                    "Tasa de PNC: 1.8% (dentro de meta <2%). Sector soldadura presentó "
                    "mayor incidencia de defectos."
                ),
                "nonconformities_status_summary": (
                    "4 NCs en el período: 1 cerrada, 1 en tratamiento, 1 en análisis, 1 abierta. "
                    "CAPA: 4 acciones, 1 completada, 1 en progreso, 2 abiertas."
                ),
                "risk_opportunity_status_summary": (
                    "8 riesgos/oportunidades identificados. 3 en tratamiento activo. "
                    "Riesgo alto: demora en entrega de acero (P4×I4=16). "
                    "Oportunidad destacada: LCM para patentamiento de chasis."
                ),
                "supplier_performance_summary": (
                    "5 proveedores activos. 2 evaluados como Aprobados. "
                    "1 Aprobado Condicionalmente (Pinturería Industrial Rosario - mejorar plazo de entrega)."
                ),
                "resource_adequacy_summary": (
                    "Recursos humanos: necesidad de 1 soldador adicional para cubrir demanda. "
                    "Infraestructura: pantógrafo requiere mantenimiento mayor programado. "
                    "Cabina de pintura tercerizada funcionando correctamente."
                ),
                "improvement_actions": (
                    "1. Implementar checklist pre-operacional en soldadura (Q1 2026)\n"
                    "2. Programa de capacitación en soldadura avanzada (Q1-Q2 2026)\n"
                    "3. Evaluar inversión en pantógrafo CNC para mejorar precisión de corte"
                ),
                "changes_to_qms": (
                    "1. Actualizar instructivos de soldadura con controles adicionales\n"
                    "2. Agregar indicador de defectos por estación de soldadura\n"
                    "3. Reforzar seguimiento del proceso de gestión del cambio (FP-02)"
                ),
                "resource_needs": (
                    "1. Contratación de 1 operario soldador calificado\n"
                    "2. Presupuesto para mantenimiento mayor de pantógrafo\n"
                    "3. Inversión en reguladores de gas nuevos para estaciones S1-S6"
                ),
                "is_active": True,
            }
        )
        self.stdout.write("  Revisión por la Dirección: 1")
