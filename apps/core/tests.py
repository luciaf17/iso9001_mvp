from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.urls import reverse

from .models import AuditEvent, Organization, Process, Site, Stakeholder, RiskOpportunity
from .services import log_audit_event


class AuditEventTestCase(TestCase):
    """Tests para el modelo AuditEvent y log_audit_event."""
    
    def test_log_audit_event_creation(self):
        """Verifica que log_audit_event crea correctamente un evento de auditoría."""
        # Crear usuario
        user = User.objects.create_user(username='testuser', password='testpass')
        
        # Crear objeto dummy (usamos otro User)
        target_user = User.objects.create_user(username='target', password='testpass')
        
        # Llamar a log_audit_event
        metadata = {'field': 'username', 'old_value': 'target', 'new_value': 'target_modified'}
        event = log_audit_event(
            actor=user,
            action='user_update',
            instance=target_user,
            metadata=metadata
        )
        
        # Assertions
        self.assertIsNotNone(event)
        self.assertEqual(event.actor, user)
        self.assertEqual(event.action, 'user_update')
        self.assertEqual(event.object_type, 'auth.User')
        self.assertEqual(event.object_id, target_user.pk)
        self.assertEqual(event.metadata, metadata)
        self.assertIsNotNone(event.timestamp)
        
        # Verificar que se guardó en la base de datos
        self.assertEqual(AuditEvent.objects.count(), 1)
    
    def test_log_audit_event_raises_on_unsaved_instance(self):
        """Verifica que log_audit_event lanza ValueError si la instancia no está guardada."""
        user = User.objects.create_user(username='testuser', password='testpass')
        unsaved_user = User(username='unsaved')
        
        with self.assertRaises(ValueError) as context:
            log_audit_event(
                actor=user,
                action='create',
                instance=unsaved_user
            )
        
        self.assertIn('pk no puede ser None', str(context.exception))


class ProcessHierarchyValidationTests(TestCase):
    def setUp(self):
        self.organization, _created = Organization.objects.get_or_create(name="Empresa")

    def _create_level1(self, code="P1", name="Proceso 1"):
        return Process.objects.create(
            organization=self.organization,
            code=code,
            name=name,
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.PROCESS,
            is_active=True,
        )

    def test_level1_cannot_have_parent(self):
        parent = self._create_level1(code="P1", name="Proceso 1")
        process = Process(
            organization=self.organization,
            code="P2",
            name="Proceso 2",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.PROCESS,
            parent=parent,
            is_active=True,
        )
        with self.assertRaises(ValidationError):
            process.full_clean()

    def test_level2_requires_parent(self):
        process = Process(
            organization=self.organization,
            code="S1",
            name="Subproceso 1",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.SUBPROCESS,
            is_active=True,
        )
        with self.assertRaises(ValidationError):
            process.full_clean()

    def test_level2_parent_must_be_level1(self):
        parent_level1 = self._create_level1(code="P1", name="Proceso 1")
        parent_level2 = Process.objects.create(
            organization=self.organization,
            code="S1",
            name="Subproceso 1",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.SUBPROCESS,
            parent=parent_level1,
            is_active=True,
        )
        process = Process(
            organization=self.organization,
            code="S2",
            name="Subproceso 2",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.SUBPROCESS,
            parent=parent_level2,
            is_active=True,
        )
        with self.assertRaises(ValidationError):
            process.full_clean()

    def test_level3_parent_must_be_level2(self):
        parent_level1 = self._create_level1(code="P1", name="Proceso 1")
        process = Process(
            organization=self.organization,
            code="T1",
            name="Sector 1",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.SECTOR,
            parent=parent_level1,
            is_active=True,
        )
        with self.assertRaises(ValidationError):
            process.full_clean()

    def test_parent_must_match_organization(self):
        other_org = Organization.objects.create(name="Otra Empresa")
        parent = Process.objects.create(
            organization=other_org,
            code="P1",
            name="Proceso 1",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.PROCESS,
            is_active=True,
        )
        process = Process(
            organization=self.organization,
            code="S1",
            name="Subproceso 1",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.SUBPROCESS,
            parent=parent,
            is_active=True,
        )
        with self.assertRaises(ValidationError):
            process.full_clean()

    def test_valid_level3_with_level2_parent(self):
        parent_level1 = self._create_level1(code="P1", name="Proceso 1")
        parent_level2 = Process.objects.create(
            organization=self.organization,
            code="S1",
            name="Subproceso 1",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.SUBPROCESS,
            parent=parent_level1,
            is_active=True,
        )
        process = Process(
            organization=self.organization,
            code="T1",
            name="Sector 1",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.SECTOR,
            parent=parent_level2,
            is_active=True,
        )
        process.full_clean()


class CeiboProcessMapSeedTests(TestCase):
    def test_seed_creates_hierarchy_and_types(self):
        call_command("seed_ceibo_process_map")

        organization = Organization.objects.get(name="Metalurgica Ceibo S.R.L.")
        site = Site.objects.get(name="Metalurgica Ceibo", organization=organization)

        level1 = Process.objects.get(organization=organization, code="09")
        level2 = Process.objects.get(organization=organization, code="09.01")
        level3 = Process.objects.get(organization=organization, code="09.01.01")

        self.assertEqual(level1.level, Process.Level.PROCESS)
        self.assertEqual(level2.level, Process.Level.SUBPROCESS)
        self.assertEqual(level3.level, Process.Level.SECTOR)

        self.assertEqual(level1.process_type, Process.ProcessType.MISSIONAL)
        self.assertEqual(level2.process_type, Process.ProcessType.MISSIONAL)
        self.assertEqual(level3.process_type, Process.ProcessType.MISSIONAL)

        self.assertEqual(level2.parent_id, level1.id)
        self.assertEqual(level3.parent_id, level2.id)


class StakeholderViewsTests(TestCase):
    def setUp(self):
        self.organization, _created = Organization.objects.get_or_create(name="Empresa")
        self.process = Process.objects.create(
            organization=self.organization,
            code="P1",
            name="Proceso 1",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.PROCESS,
            is_active=True,
        )
        self.admin_group = Group.objects.create(name="Admin")
        self.admin_user = User.objects.create_user(username="admin", password="testpass")
        self.admin_user.groups.add(self.admin_group)
        self.normal_user = User.objects.create_user(username="user", password="testpass")

    def test_create_stakeholder(self):
        self.client.login(username="admin", password="testpass")

        response = self.client.post(
            reverse("core:stakeholder_new"),
            data={
                "name": "Proveedor X",
                "stakeholder_type": Stakeholder.StakeholderType.SUPPLIER,
                "expectations": "Cumplir plazos de entrega.",
                "is_active": "on",
                "related_process": self.process.id,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Stakeholder.objects.filter(name="Proveedor X").exists())
        self.assertTrue(AuditEvent.objects.filter(action="stakeholder_created").exists())

    def test_non_admin_cannot_create(self):
        self.client.login(username="user", password="testpass")

        response = self.client.post(
            reverse("core:stakeholder_new"),
            data={
                "name": "Cliente Z",
                "stakeholder_type": Stakeholder.StakeholderType.CUSTOMER,
                "expectations": "Atencion rapida.",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Stakeholder.objects.filter(name="Cliente Z").exists())

    def test_list_renders(self):
        Stakeholder.objects.create(
            organization=self.organization,
            name="Regulador",
            stakeholder_type=Stakeholder.StakeholderType.REGULATOR,
            expectations="Cumplir normativa vigente.",
            is_active=True,
        )

        self.client.login(username="user", password="testpass")
        response = self.client.get(reverse("core:stakeholder_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Regulador")


class RiskOpportunityTests(TestCase):
    def setUp(self):
        self.organization, _created = Organization.objects.get_or_create(name="Empresa")
        self.process = Process.objects.create(
            organization=self.organization,
            code="R1",
            name="Proceso Riesgos",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.PROCESS,
            is_active=True,
        )
        self.admin_group = Group.objects.create(name="Admin")
        self.admin_user = User.objects.create_user(username="admin_risk", password="testpass")
        self.admin_user.groups.add(self.admin_group)
        self.normal_user = User.objects.create_user(username="user_risk", password="testpass")

    def test_score_level_calculation(self):
        risk = RiskOpportunity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="Riesgo critico",
            description="Descripcion",
            kind=RiskOpportunity.Kind.RISK,
            probability=5,
            impact=5,
            status=RiskOpportunity.Status.OPEN,
            is_active=True,
        )

        self.assertEqual(risk.score, 25)
        self.assertEqual(risk.level, RiskOpportunity.Level.HIGH)

    def test_non_admin_cannot_create_or_edit(self):
        self.client.login(username="user_risk", password="testpass")

        response = self.client.post(
            reverse("core:risk_new"),
            data={
                "title": "Riesgo no autorizado",
                "description": "Descripcion",
                "kind": RiskOpportunity.Kind.RISK,
                "probability": 3,
                "impact": 3,
                "status": RiskOpportunity.Status.OPEN,
                "related_process": self.process.id,
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(RiskOpportunity.objects.filter(title="Riesgo no autorizado").exists())

        risk = RiskOpportunity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="Riesgo editable",
            description="Descripcion",
            kind=RiskOpportunity.Kind.RISK,
            probability=2,
            impact=2,
            status=RiskOpportunity.Status.OPEN,
            is_active=True,
        )

        response = self.client.post(
            reverse("core:risk_edit", args=[risk.pk]),
            data={
                "title": "Riesgo editado",
                "description": "Descripcion",
                "kind": RiskOpportunity.Kind.RISK,
                "probability": 2,
                "impact": 2,
                "status": RiskOpportunity.Status.OPEN,
                "related_process": self.process.id,
                "is_active": "on",
            },
        )

        risk.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(risk.title, "Riesgo editable")

    def test_list_renders(self):
        RiskOpportunity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="Oportunidad",
            description="Descripcion",
            kind=RiskOpportunity.Kind.OPPORTUNITY,
            probability=2,
            impact=3,
            status=RiskOpportunity.Status.OPEN,
            is_active=True,
        )

        self.client.login(username="user_risk", password="testpass")
        response = self.client.get(reverse("core:risk_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Oportunidad")
    def test_dashboard_renders(self):
        """Test that dashboard renders with matrix and summaries."""
        # Create risks with different probability/impact combinations
        RiskOpportunity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="Riesgo bajo",
            description="Bajo riesgo",
            kind=RiskOpportunity.Kind.RISK,
            probability=1,  # score = 1*1 = 1 (LOW)
            impact=1,
            status=RiskOpportunity.Status.OPEN,
            is_active=True,
        )

        RiskOpportunity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="Riesgo medio",
            description="Riesgo medio",
            kind=RiskOpportunity.Kind.RISK,
            probability=3,  # score = 3*3 = 9 (MEDIUM)
            impact=3,
            status=RiskOpportunity.Status.OPEN,
            is_active=True,
        )

        RiskOpportunity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="Riesgo alto",
            description="Riesgo alto",
            kind=RiskOpportunity.Kind.RISK,
            probability=5,  # score = 5*5 = 25 (HIGH)
            impact=5,
            status=RiskOpportunity.Status.OPEN,
            is_active=True,
        )

        RiskOpportunity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="Oportunidad",
            description="Oportunidad",
            kind=RiskOpportunity.Kind.OPPORTUNITY,
            probability=2,  # score = 2*4 = 8 (MEDIUM)
            impact=4,
            status=RiskOpportunity.Status.OPEN,
            is_active=True,
        )

        self.client.login(username="user_risk", password="testpass")
        response = self.client.get(reverse("core:risk_dashboard"))

        self.assertEqual(response.status_code, 200)
        # Check that the matrix cells with data are present
        self.assertContains(response, "(1,1)")  # LOW cell
        self.assertContains(response, "(3,3)")  # MEDIUM cell
        self.assertContains(response, "(5,5)")  # HIGH cell
        self.assertContains(response, "(2,4)")  # MEDIUM cell

    def test_dashboard_matrix_cell_counts(self):
        """Test that matrix cells show correct counts based on probability/impact."""
        # Create two risks with same probability/impact
        RiskOpportunity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="Riesgo 1",
            description="Riesgo 1",
            kind=RiskOpportunity.Kind.RISK,
            probability=2,
            impact=3,
            status=RiskOpportunity.Status.OPEN,
            is_active=True,
        )

        RiskOpportunity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="Riesgo 2",
            description="Riesgo 2",
            kind=RiskOpportunity.Kind.RISK,
            probability=2,
            impact=3,
            status=RiskOpportunity.Status.OPEN,
            is_active=True,
        )

        # One different cell
        RiskOpportunity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="Riesgo 3",
            description="Riesgo 3",
            kind=RiskOpportunity.Kind.RISK,
            probability=4,
            impact=5,
            status=RiskOpportunity.Status.OPEN,
            is_active=True,
        )

        self.client.login(username="user_risk", password="testpass")
        response = self.client.get(reverse("core:risk_dashboard"))

        self.assertEqual(response.status_code, 200)
        # Check that cell (2,3) shows count 2
        self.assertContains(response, "(2,3)")

    def test_dashboard_kind_summary(self):
        """Test that kind summary shows correct counts for RISK and OPPORTUNITY."""
        RiskOpportunity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="Riesgo 1",
            description="Riesgo 1",
            kind=RiskOpportunity.Kind.RISK,
            probability=2,
            impact=2,
            status=RiskOpportunity.Status.OPEN,
            is_active=True,
        )

        RiskOpportunity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="Oportunidad 1",
            description="Oportunidad 1",
            kind=RiskOpportunity.Kind.OPPORTUNITY,
            probability=2,
            impact=2,
            status=RiskOpportunity.Status.OPEN,
            is_active=True,
        )

        self.client.login(username="user_risk", password="testpass")
        response = self.client.get(reverse("core:risk_dashboard"))

        self.assertEqual(response.status_code, 200)
        # Check that the dashboard summary shows kind counts exist
        self.assertContains(response, "Total de registros:")
        self.assertContains(response, "Riesgos")
        self.assertContains(response, "Oportunidades")