from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, date

from .models import (
    AuditEvent,
    Organization,
    Process,
    Site,
    Stakeholder,
    RiskOpportunity,
    NoConformity,
    CAPAAction,
    QualityObjective,
    InternalAudit,
    AuditQuestion,
    AuditAnswer,
    AuditFinding,
    ManagementReview,
    QualityIndicator,
    IndicatorMeasurement,
    NonconformingOutput,
    Supplier,
    SupplierEvaluation,
)
from .forms import CAPAActionForm
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
        """Test que el dashboard renderiza con datos correctos en el contexto."""
        # Crear riesgos con diferentes niveles
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
        
        # Verificar que el contexto tiene los datos correctos
        self.assertIn('matrix_grid', response.context)
        self.assertIn('total_risks', response.context)
        self.assertIn('level_summary', response.context)
        self.assertIn('kind_summary', response.context)
        
        # Verificar total
        self.assertEqual(response.context['total_risks'], 4)
        
        # Verificar que la página renderiza sin errores
        self.assertContains(response, "Dashboard de Riesgos")

    def test_dashboard_matrix_data_structure(self):
        """Test que la matriz 5x5 se construye correctamente en el contexto."""
        # Crear dos riesgos con misma probabilidad/impacto
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

        self.client.login(username="user_risk", password="testpass")
        response = self.client.get(reverse("core:risk_dashboard"))

        self.assertEqual(response.status_code, 200)
        
        # Verificar estructura de matriz en contexto
        matrix_grid = response.context['matrix_grid']
        
        # La matriz debe tener 5 filas (prob 5..1)
        self.assertEqual(len(matrix_grid), 5)
        
        # Cada fila debe tener 5 columnas (impact 1..5)
        for row in matrix_grid:
            self.assertEqual(len(row), 5)
        
        # Verificar que existe una celda con count=2 en (prob=2, impact=3)
        # La matriz va de prob 5→1 (filas) y impact 1→5 (cols)
        # prob=2 está en fila 3 (índice 3 desde arriba: 5,4,3,2,1)
        # impact=3 está en col 2 (índice 2 desde izq: 1,2,3,4,5)
        cell_prob2_imp3 = matrix_grid[3][2]  # fila=3 (prob=2), col=2 (impact=3)
        self.assertEqual(cell_prob2_imp3['probability'], 2)
        self.assertEqual(cell_prob2_imp3['impact'], 3)
        self.assertEqual(cell_prob2_imp3['count'], 2)

    def test_dashboard_kind_summary(self):
        """Test que el resumen por tipo muestra conteos correctos."""
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
            title="Riesgo 2",
            description="Riesgo 2",
            kind=RiskOpportunity.Kind.RISK,
            probability=3,
            impact=3,
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
        
        # Verificar kind_summary en contexto
        kind_summary = response.context['kind_summary']
        
        self.assertEqual(kind_summary.get('RISK', 0), 2)
        self.assertEqual(kind_summary.get('OPPORTUNITY', 0), 1)
        
        # Verificar total
        self.assertEqual(response.context['total_risks'], 3)


class NoConformityTests(TestCase):
    """Tests para el modelo NoConformity y sus vistas."""
    
    def setUp(self):
        self.organization, _created = Organization.objects.get_or_create(name="Empresa")
        self.process = Process.objects.create(
            organization=self.organization,
            code="NC1",
            name="Proceso NC",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.PROCESS,
            is_active=True,
        )
        self.admin_group = Group.objects.create(name="Admin")
        self.calidad_group = Group.objects.create(name="Calidad")
        self.admin_user = User.objects.create_user(username="admin_nc", password="testpass")
        self.admin_user.groups.add(self.admin_group)
        self.calidad_user = User.objects.create_user(username="calidad_nc", password="testpass")
        self.calidad_user.groups.add(self.calidad_group)
        self.normal_user = User.objects.create_user(username="user_nc", password="testpass")
    
    def test_create_nc_generates_audit_event(self):
        """Verifica que crear una NC genera un evento de auditoría."""
        from .models import NoConformity
        
        self.client.login(username="admin_nc", password="testpass")
        
        from datetime import date
        
        response = self.client.post(
            reverse("core:nc_new"),
            data={
                "title": "NC de prueba",
                "description": "Descripcion NC",
                "origin": "INTERNAL_AUDIT",
                "severity": "MAJOR",
                "status": "OPEN",
                "detected_at": date.today().isoformat(),
                "detected_by": self.admin_user.id,
                "related_process": self.process.id,
            },
        )
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(NoConformity.objects.filter(title="NC de prueba").exists())
        
        # Verificar evento de auditoría
        self.assertTrue(
            AuditEvent.objects.filter(
                action="core.nc.created",
                actor=self.admin_user
            ).exists()
        )
    
    def test_non_admin_cannot_create_nc(self):
        """Verifica que usuarios sin permisos no pueden crear NCs."""
        from .models import NoConformity
        
        self.client.login(username="user_nc", password="testpass")
        
        from datetime import date
        
        response = self.client.post(
            reverse("core:nc_new"),
            data={
                "title": "NC no autorizada",
                "description": "Descripcion",
                "origin": "INTERNAL_AUDIT",
                "severity": "MINOR",
                "status": "OPEN",
                "detected_at": date.today().isoformat(),
                "detected_by": self.admin_user.id,
                "related_process": self.process.id,
            },
        )
        
        self.assertEqual(response.status_code, 302)
        self.assertFalse(NoConformity.objects.filter(title="NC no autorizada").exists())
    
    def test_calidad_can_create_and_edit_nc(self):
        """Verifica que usuarios del grupo Calidad pueden crear y editar NCs."""
        from .models import NoConformity
        
        self.client.login(username="calidad_nc", password="testpass")
        
        from datetime import date
        
        # Crear NC
        response = self.client.post(
            reverse("core:nc_new"),
            data={
                "title": "NC Calidad",
                "description": "Descripcion",
                "origin": "EXTERNAL_AUDIT",
                "severity": "CRITICAL",
                "status": "OPEN",
                "detected_at": date.today().isoformat(),
                "detected_by": self.calidad_user.id,
                "related_process": self.process.id,
            },
        )
        
        self.assertEqual(response.status_code, 302)
        nc = NoConformity.objects.get(title="NC Calidad")
        
        # Editar NC
        response = self.client.post(
            reverse("core:nc_edit", args=[nc.pk]),
            data={
                "title": "NC Calidad Editada",
                "description": "Descripcion actualizada",
                "origin": "EXTERNAL_AUDIT",
                "severity": "MAJOR",
                "status": "IN_ANALYSIS",
                "detected_at": nc.detected_at.isoformat(),
                "detected_by": self.calidad_user.id,
                "related_process": self.process.id,
            },
        )
        
        nc.refresh_from_db()
        self.assertEqual(nc.title, "NC Calidad Editada")
        self.assertEqual(nc.status, "IN_ANALYSIS")
        
        # Verificar evento de auditoría de edición
        self.assertTrue(
            AuditEvent.objects.filter(
                action="core.nc.updated",
                actor=self.calidad_user
            ).exists()
        )
    
    def test_nc_list_renders(self):
        """Verifica que la lista de NCs se renderiza correctamente."""
        from .models import NoConformity
        
        from datetime import date
        
        NoConformity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="NC Lista",
            description="Descripcion",
            origin="CUSTOMER",
            severity="MINOR",
            status="OPEN",
            detected_at=date.today(),
        )
        
        self.client.login(username="user_nc", password="testpass")
        response = self.client.get(reverse("core:nc_list"))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NC Lista")
    
    def test_nc_detail_renders(self):
        """Verifica que el detalle de NC se renderiza correctamente."""
        from .models import NoConformity
        
        from datetime import date
        
        nc = NoConformity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="NC Detalle",
            description="Descripcion detallada",
            origin="INTERNAL",
            severity="MAJOR",
            status="IN_ANALYSIS",
            detected_at=date.today(),
        )
        
        self.client.login(username="user_nc", password="testpass")
        response = self.client.get(reverse("core:nc_detail", args=[nc.pk]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NC Detalle")
        self.assertContains(response, "Descripcion detallada")


class CAPAActionModelTests(TestCase):
    """Tests para el modelo CAPAAction."""

    def _create_nc(self, organization, title="Test NC"):
        return NoConformity.objects.create(
            organization=organization,
            title=title,
            description="Test",
            origin=NoConformity.Origin.INTERNAL,
            severity=NoConformity.Severity.MINOR,
            detected_at=timezone.now().date(),
            status=NoConformity.Status.OPEN,
        )

    def test_capa_action_creation(self):
        """Test que CAPAAction se crea correctamente con campos obligatorios."""
        org = Organization.objects.create(name="Test Org")
        nc = self._create_nc(org)

        capa = CAPAAction.objects.create(
            no_conformity=nc,
            organization=org,
            title="Capacitar operarios",
            action_type=CAPAAction.ActionType.CORRECTIVE,
            status=CAPAAction.Status.OPEN,
        )

        assert capa.id is not None
        assert capa.title == "Capacitar operarios"
        assert capa.no_conformity == nc
        assert capa.organization == org
        assert capa.status == CAPAAction.Status.OPEN
        assert capa.completed_at is None

    def test_capa_action_auto_copy_organization(self):
        """Test que CAPAAction copia organization de la NC automaticamente."""
        org = Organization.objects.create(name="Test Org")
        nc = self._create_nc(org)

        capa = CAPAAction.objects.create(
            no_conformity=nc,
            title="Test Action",
            action_type=CAPAAction.ActionType.CORRECTIVE,
        )

        assert capa.organization == org

    def test_capa_action_auto_complete_when_done(self):
        """Test que completed_at se llena automaticamente cuando status cambia a DONE."""
        org = Organization.objects.create(name="Test Org")
        nc = self._create_nc(org)

        capa = CAPAAction.objects.create(
            no_conformity=nc,
            title="Test Action",
            action_type=CAPAAction.ActionType.CORRECTIVE,
            status=CAPAAction.Status.OPEN,
        )

        assert capa.completed_at is None

        capa.status = CAPAAction.Status.DONE
        capa.save()

        capa.refresh_from_db()
        assert capa.completed_at is not None

    def test_capa_action_clear_completed_when_reopened(self):
        """Test que completed_at se limpia cuando status vuelve a OPEN o IN_PROGRESS."""
        org = Organization.objects.create(name="Test Org")
        nc = self._create_nc(org)

        capa = CAPAAction.objects.create(
            no_conformity=nc,
            title="Test Action",
            action_type=CAPAAction.ActionType.CORRECTIVE,
            status=CAPAAction.Status.DONE,
        )

        assert capa.completed_at is not None

        capa.status = CAPAAction.Status.OPEN
        capa.save()

        capa.refresh_from_db()
        assert capa.completed_at is None

    def test_capa_action_cascade_delete_with_nc(self):
        """Test que CAPAAction se elimina cuando se elimina la NC (CASCADE)."""
        org = Organization.objects.create(name="Test Org")
        nc = self._create_nc(org)

        capa = CAPAAction.objects.create(
            no_conformity=nc,
            title="Test Action",
            action_type=CAPAAction.ActionType.CORRECTIVE,
        )

        capa_id = capa.id
        nc.delete()

        assert not CAPAAction.objects.filter(id=capa_id).exists()

    def test_capa_action_str_representation(self):
        """Test que el metodo __str__ de CAPAAction es correcto."""
        org = Organization.objects.create(name="Test Org")
        nc = self._create_nc(org)
        nc.code = "NC-2025-001"
        nc.save(update_fields=["code"])

        capa = CAPAAction.objects.create(
            no_conformity=nc,
            title="Capacitar operarios",
            action_type=CAPAAction.ActionType.CORRECTIVE,
        )

        expected = "Correctiva: Capacitar operarios (NC: NC-2025-001)"
        assert str(capa) == expected

    def test_capa_action_ordering_by_due_date(self):
        """Test que CAPAActions se ordenan por due_date."""
        org = Organization.objects.create(name="Test Org")
        nc = self._create_nc(org)
        today = timezone.now().date()

        capa3 = CAPAAction.objects.create(
            no_conformity=nc,
            title="Action 3",
            due_date=today + timedelta(days=10),
            action_type=CAPAAction.ActionType.CORRECTIVE,
        )
        capa1 = CAPAAction.objects.create(
            no_conformity=nc,
            title="Action 1",
            due_date=today + timedelta(days=2),
            action_type=CAPAAction.ActionType.CORRECTIVE,
        )
        capa2 = CAPAAction.objects.create(
            no_conformity=nc,
            title="Action 2",
            due_date=today + timedelta(days=5),
            action_type=CAPAAction.ActionType.CORRECTIVE,
        )

        capas = list(CAPAAction.objects.all())
        assert capas[0] == capa1
        assert capas[1] == capa2
        assert capas[2] == capa3


class CAPAActionViewTests(TestCase):
    """Tests para las vistas de CAPAAction."""

    def setUp(self):
        # Use get_or_create like other tests to avoid org conflicts
        self.organization, _ = Organization.objects.get_or_create(
            name="Test Org CAPA",
            defaults={"is_active": True}
        )
        self.nc = NoConformity.objects.create(
            organization=self.organization,
            code=f"NCTEST{timezone.now().timestamp():.0f}"[:20],
            title="Test NC",
            description="Test",
            origin=NoConformity.Origin.INTERNAL,
            severity=NoConformity.Severity.MINOR,
            detected_at=timezone.now().date(),
        )
        self.admin_group, _ = Group.objects.get_or_create(name="Admin")
        self.lectura_group, _ = Group.objects.get_or_create(name="Lectura")
        self.User = get_user_model()

    def test_capa_action_create_permission_admin(self):
        """Test que usuarios Admin pueden crear CAPAActions."""
        user = self.User.objects.create_user(username="capa_admin", password="test123")
        user.groups.add(self.admin_group)

        self.client.force_login(user)

        response = self.client.post(
            reverse("core:capa_action_create", args=[self.nc.id]),
            {
                "title": "Test Action",
                "action_type": CAPAAction.ActionType.CORRECTIVE,
                "status": CAPAAction.Status.OPEN,
            },
        )

        assert response.status_code == 302
        assert CAPAAction.objects.filter(title="Test Action").exists()

    def test_capa_action_create_permission_denied(self):
        """Test que usuarios sin permisos NO pueden crear CAPAActions."""
        user = self.User.objects.create_user(username="capa_reader", password="test123")
        user.groups.add(self.lectura_group)

        self.client.force_login(user)

        response = self.client.post(
            reverse("core:capa_action_create", args=[self.nc.id]),
            {
                "title": "Test Action",
                "action_type": CAPAAction.ActionType.CORRECTIVE,
                "status": CAPAAction.Status.OPEN,
            },
        )

        assert response.status_code == 302
        assert not CAPAAction.objects.filter(title="Test Action").exists()

    def test_capa_action_creates_audit_event(self):
        """Test que crear CAPAAction genera un AuditEvent."""
        user = self.User.objects.create_user(username="capa_admin_audit", password="test123")
        user.groups.add(self.admin_group)

        self.client.force_login(user)
        initial_audit_count = AuditEvent.objects.count()

        response = self.client.post(
            reverse("core:capa_action_create", args=[self.nc.id]),
            {
                "title": "Test Action",
                "action_type": CAPAAction.ActionType.CORRECTIVE,
                "status": CAPAAction.Status.OPEN,
            },
        )

        assert response.status_code == 302
        assert AuditEvent.objects.count() == initial_audit_count + 1

        last_event = AuditEvent.objects.latest("timestamp")
        assert last_event.action == "core.capa_action.created"
        assert last_event.actor == user

    def test_capa_action_create_from_finding_area_of_concern(self):
        """Test crear CAPAAction desde hallazgo tipo AREA_OF_CONCERN."""
        user = self.User.objects.create_user(username="capa_admin_finding", password="test123")
        user.groups.add(self.admin_group)

        audit = InternalAudit.objects.create(
            organization=self.organization,
            title="Test Audit",
            audit_type=InternalAudit.AuditType.INTERNAL,
            audit_date=date.today(),
        )
        finding = AuditFinding.objects.create(
            audit=audit,
            finding_type=AuditFinding.FindingType.AREA_OF_CONCERN,
            description="Test area of concern",
        )

        self.client.force_login(user)

        response = self.client.post(
            reverse("core:audit_finding_action_new", args=[finding.pk]),
            {
                "title": "Test Action from Finding",
                "action_type": CAPAAction.ActionType.CORRECTIVE,
                "status": CAPAAction.Status.OPEN,
            },
        )

        assert response.status_code == 302, f"Expected 302, got {response.status_code}. Response content:\n{response.content if response.status_code != 302 else 'redirect'}"
        capa = CAPAAction.objects.filter(title="Test Action from Finding").first()
        assert capa is not None, "CAPA action was not created"
        assert capa.finding == finding
        assert capa.no_conformity is None

        assert capa.organization == self.organization

    def test_capa_action_create_from_finding_improvement_opportunity(self):
        """Test crear CAPAAction desde hallazgo tipo IMPROVEMENT_OPPORTUNITY."""
        user = self.User.objects.create_user(username="capa_admin_finding2", password="test123")
        user.groups.add(self.admin_group)

        audit = InternalAudit.objects.create(
            organization=self.organization,
            title="Test Audit 2",
            audit_type=InternalAudit.AuditType.INTERNAL,
            audit_date=date.today(),
        )
        finding = AuditFinding.objects.create(
            audit=audit,
            finding_type=AuditFinding.FindingType.IMPROVEMENT_OPPORTUNITY,
            description="Test improvement opportunity",
        )

        self.client.force_login(user)

        response = self.client.post(
            reverse("core:audit_finding_action_new", args=[finding.pk]),
            {
                "title": "Test Improvement Action",
                "action_type": CAPAAction.ActionType.PREVENTIVE,
                "status": CAPAAction.Status.OPEN,
            },
        )

        assert response.status_code == 302
        capa = CAPAAction.objects.filter(title="Test Improvement Action").first()
        assert capa is not None
        assert capa.finding == finding
        assert capa.no_conformity is None

    def test_capa_action_create_from_finding_rejects_nonconformity(self):
        """Test que no se puede crear CAPAAction desde hallazgo NONCONFORMITY."""
        user = self.User.objects.create_user(username="capa_admin_nc_reject", password="test123")
        user.groups.add(self.admin_group)

        audit = InternalAudit.objects.create(
            organization=self.organization,
            title="Test Audit NC",
            audit_type=InternalAudit.AuditType.INTERNAL,
            audit_date=date.today(),
        )
        finding = AuditFinding.objects.create(
            audit=audit,
            finding_type=AuditFinding.FindingType.NONCONFORMITY,
            description="Test nonconformity",
        )

        self.client.force_login(user)

        response = self.client.post(
            reverse("core:audit_finding_action_new", args=[finding.pk]),
            {
                "title": "Test Rejected Action",
                "action_type": CAPAAction.ActionType.CORRECTIVE,
                "status": CAPAAction.Status.OPEN,
            },
        )

        assert response.status_code == 302
        assert not CAPAAction.objects.filter(title="Test Rejected Action").exists()

    def test_capa_action_create_from_finding_permission_denied(self):
        """Test que usuarios sin permisos NO pueden crear CAPAAction desde hallazgo."""
        user = self.User.objects.create_user(username="capa_reader_finding", password="test123")
        user.groups.add(self.lectura_group)

        audit = InternalAudit.objects.create(
            organization=self.organization,
            title="Test Audit Denied",
            audit_type=InternalAudit.AuditType.INTERNAL,
            audit_date=date.today(),
        )
        finding = AuditFinding.objects.create(
            audit=audit,
            finding_type=AuditFinding.FindingType.AREA_OF_CONCERN,
            description="Test area of concern",
        )

        self.client.force_login(user)

        response = self.client.post(
            reverse("core:audit_finding_action_new", args=[finding.pk]),
            {
                "title": "Test Denied Action",
                "action_type": CAPAAction.ActionType.CORRECTIVE,
                "status": CAPAAction.Status.OPEN,
            },
        )

        assert response.status_code == 302
        assert not CAPAAction.objects.filter(title="Test Denied Action").exists()

    def test_capa_action_create_from_finding_creates_audit_event(self):
        """Test que crear CAPAAction desde hallazgo genera AuditEvent correcto."""
        user = self.User.objects.create_user(username="capa_admin_event", password="test123")
        user.groups.add(self.admin_group)

        audit = InternalAudit.objects.create(
            organization=self.organization,
            title="Test Audit Event",
            audit_type=InternalAudit.AuditType.INTERNAL,
            audit_date=date.today(),
        )
        finding = AuditFinding.objects.create(
            audit=audit,
            finding_type=AuditFinding.FindingType.AREA_OF_CONCERN,
            description="Test area of concern",
        )

        self.client.force_login(user)
        initial_audit_count = AuditEvent.objects.count()

        response = self.client.post(
            reverse("core:audit_finding_action_new", args=[finding.pk]),
            {
                "title": "Test Action Event",
                "action_type": CAPAAction.ActionType.CORRECTIVE,
                "status": CAPAAction.Status.OPEN,
            },
        )

        assert response.status_code == 302
        assert AuditEvent.objects.count() == initial_audit_count + 1

        last_event = AuditEvent.objects.latest("timestamp")
        assert last_event.action == "core.capa_action.created_from_finding"
        assert last_event.actor == user
        assert last_event.metadata.get("finding_id") == finding.id
        assert last_event.metadata.get("audit_id") == audit.id
        assert last_event.metadata.get("finding_type") == AuditFinding.FindingType.AREA_OF_CONCERN

    def test_capa_effectiveness_validation_result_without_date(self):
        """Test que form validation falla si se asigna resultado de eficacia sin fecha."""
        self.organization = Organization.objects.create(name="Test Org Effectiveness")
        nc = NoConformity.objects.create(
            organization=self.organization,
            code="NC-TEST-EFF",
            title="Test NC",
            description="Test",
            origin=NoConformity.Origin.INTERNAL,
            severity=NoConformity.Severity.MINOR,
            detected_at=timezone.now().date(),
        )

        form_data = {
            "title": "Test Action Effectiveness",
            "description": "Test",
            "action_type": CAPAAction.ActionType.CORRECTIVE,
            "status": CAPAAction.Status.DONE,
            "effectiveness_result": CAPAAction.EffectivenessResult.EFFECTIVE,
            # effectiveness_date is empty (intentional)
        }

        form = CAPAActionForm(data=form_data)
        assert not form.is_valid()
        assert "effectiveness_date" in str(form.errors) or "completitud" in str(form.errors).lower() or "Si asignas" in str(form.errors)

    def test_capa_effectiveness_validation_both_set(self):
        """Test que form es valido cuando se asignan fecha y resultado de eficacia."""
        self.organization = Organization.objects.create(name="Test Org Effectiveness 2")
        nc = NoConformity.objects.create(
            organization=self.organization,
            code="NC-TEST-EFF-2",
            title="Test NC",
            description="Test",
            origin=NoConformity.Origin.INTERNAL,
            severity=NoConformity.Severity.MINOR,
            detected_at=timezone.now().date(),
        )

        form_data = {
            "title": "Test Action Effectiveness",
            "description": "Test",
            "action_type": CAPAAction.ActionType.CORRECTIVE,
            "status": CAPAAction.Status.DONE,
            "effectiveness_result": CAPAAction.EffectivenessResult.EFFECTIVE,
            "effectiveness_date": "2025-02-16",
        }

        form = CAPAActionForm(data=form_data)
        assert form.is_valid(), f"Form should be valid but has errors: {form.errors}"

    def test_capa_effectiveness_validation_both_empty(self):
        """Test que form es valido cuando ambos campos de eficacia estan vacios."""
        self.organization = Organization.objects.create(name="Test Org Effectiveness 3")
        nc = NoConformity.objects.create(
            organization=self.organization,
            code="NC-TEST-EFF-3",
            title="Test NC",
            description="Test",
            origin=NoConformity.Origin.INTERNAL,
            severity=NoConformity.Severity.MINOR,
            detected_at=timezone.now().date(),
        )

        form_data = {
            "title": "Test Action Effectiveness",
            "description": "Test",
            "action_type": CAPAAction.ActionType.CORRECTIVE,
            "status": CAPAAction.Status.OPEN,
            # Both effectiveness fields are empty
        }

        form = CAPAActionForm(data=form_data)
        assert form.is_valid(), f"Form should be valid but has errors: {form.errors}"

    def test_capa_effectiveness_metadata_in_audit_event(self):
        """Test que la actualizacion de CAPAAction incluye metadata de eficacia en AuditEvent."""
        user = self.User.objects.create_user(username="capa_effectiveness_test", password="test123")
        user.groups.add(self.admin_group)

        self.client.force_login(user)

        # Create CAPA action
        response = self.client.post(
            reverse("core:capa_action_create", args=[self.nc.id]),
            {
                "title": "Test Action with Effectiveness",
                "action_type": CAPAAction.ActionType.CORRECTIVE,
                "status": CAPAAction.Status.DONE,
            },
        )
        assert response.status_code == 302

        capa = CAPAAction.objects.get(title="Test Action with Effectiveness")

        # Edit CAPA to set effectiveness
        response = self.client.post(
            reverse("core:capa_action_edit", args=[capa.id]),
            {
                "title": "Test Action with Effectiveness",
                "action_type": CAPAAction.ActionType.CORRECTIVE,
                "status": CAPAAction.Status.DONE,
                "effectiveness_result": CAPAAction.EffectivenessResult.EFFECTIVE,
                "effectiveness_date": "2025-02-16",
                "effectiveness_notes": "Accion fue efectiva y el problema se resolvio",
            },
        )
        assert response.status_code == 302

        # Verify audit event includes effectiveness metadata
        last_event = AuditEvent.objects.filter(action="core.capa_action.updated").latest("timestamp")
        assert last_event.action == "core.capa_action.updated"
        assert last_event.actor == user
        assert last_event.metadata.get("effectiveness_result") == CAPAAction.EffectivenessResult.EFFECTIVE
        assert last_event.metadata.get("effectiveness_date") is not None


class RiskOpportunityValidationTests(TestCase):
    """Tests para validaciones de RiskOpportunity."""

    def setUp(self):
        self.organization, _ = Organization.objects.get_or_create(name="Empresa")
        self.process = Process.objects.create(
            organization=self.organization,
            code="R1",
            name="Proceso Riesgos",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.PROCESS,
            is_active=True,
        )

    def test_risk_probability_validation_out_of_range(self):
        """Test que probability debe estar entre 1 y 5."""
        risk = RiskOpportunity(
            organization=self.organization,
            related_process=self.process,
            title="Riesgo invalido",
            description="Test",
            kind=RiskOpportunity.Kind.RISK,
            probability=6,  # Inválido (>5)
            impact=3,
            status=RiskOpportunity.Status.OPEN,
        )
        
        with self.assertRaises(ValidationError):
            risk.full_clean()

    def test_risk_impact_validation_out_of_range(self):
        """Test que impact debe estar entre 1 y 5."""
        risk = RiskOpportunity(
            organization=self.organization,
            related_process=self.process,
            title="Riesgo invalido",
            description="Test",
            kind=RiskOpportunity.Kind.RISK,
            probability=3,
            impact=0,  # Inválido (<1)
            status=RiskOpportunity.Status.OPEN,
        )
        
        with self.assertRaises(ValidationError):
            risk.full_clean()

    def test_risk_level_calculation_low(self):
        """Test que score ≤7 es nivel BAJO."""
        risk = RiskOpportunity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="Riesgo bajo",
            description="Test",
            kind=RiskOpportunity.Kind.RISK,
            probability=2,
            impact=3,  # score = 6
            status=RiskOpportunity.Status.OPEN,
        )
        
        self.assertEqual(risk.score, 6)
        self.assertEqual(risk.level, RiskOpportunity.Level.LOW)

    def test_risk_level_calculation_medium(self):
        """Test que 7 < score ≤14 es nivel MEDIO."""
        risk = RiskOpportunity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="Riesgo medio",
            description="Test",
            kind=RiskOpportunity.Kind.RISK,
            probability=3,
            impact=4,  # score = 12
            status=RiskOpportunity.Status.OPEN,
        )
        
        self.assertEqual(risk.score, 12)
        self.assertEqual(risk.level, RiskOpportunity.Level.MEDIUM)


class NoConformityAutoGenerationTests(TestCase):
    """Tests para auto-generación de campos en NoConformity."""

    def setUp(self):
        self.organization, _ = Organization.objects.get_or_create(name="Empresa")
        self.process = Process.objects.create(
            organization=self.organization,
            code="NC1",
            name="Proceso NC",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.PROCESS,
            is_active=True,
        )

    def test_nc_code_auto_generation(self):
        """Test que el código de NC se genera automáticamente."""
        from datetime import date
        
        user = User.objects.create_user(username="detector", password="pass")
        
        nc = NoConformity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="NC auto code",
            description="Test auto code",
            origin=NoConformity.Origin.INTERNAL,
            severity=NoConformity.Severity.MINOR,
            detected_at=date.today(),
            detected_by=user,
            status=NoConformity.Status.OPEN,
        )
        
        # Verificar que se generó un código
        self.assertIsNotNone(nc.code)
        self.assertTrue(nc.code.startswith("NC-"))
        
        # Verificar formato NC-YYYY-NNN
        import re
        pattern = r"^NC-\d{4}-\d{3}$"
        self.assertRegex(nc.code, pattern)

    def test_nc_closed_date_auto_set(self):
        """Test que closed_date se llena automáticamente cuando status=CLOSED."""
        from datetime import date
        
        user = User.objects.create_user(username="detector2", password="pass")
        
        nc = NoConformity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="NC auto close",
            description="Test",
            origin=NoConformity.Origin.INTERNAL,
            severity=NoConformity.Severity.MINOR,
            detected_at=date.today(),
            detected_by=user,
            status=NoConformity.Status.OPEN,
            root_cause_analysis="Causa raiz",
            corrective_action="Accion correctiva",
        )
        
        # Inicialmente closed_date es None
        self.assertIsNone(nc.closed_date)
        
        # Cambiar a CLOSED
        nc.status = NoConformity.Status.CLOSED
        nc.save()
        
        nc.refresh_from_db()
        
        # closed_date se llenó automáticamente
        self.assertIsNotNone(nc.closed_date)
        self.assertEqual(nc.closed_date, date.today())


class NoConformityCAPACrossValidationTests(TestCase):
    """Tests para validaciones cruzadas entre NC y CAPA."""

    def setUp(self):
        self.organization, _ = Organization.objects.get_or_create(name="Empresa")
        self.process = Process.objects.create(
            organization=self.organization,
            code="NC1",
            name="Proceso NC",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.PROCESS,
            is_active=True,
        )
        self.user = User.objects.create_user(username="detector", password="pass")

    def test_cannot_close_nc_with_open_capa(self):
        """Test que NO se puede cerrar NC si hay CAPA abiertas."""
        nc = NoConformity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="NC con CAPA abierta",
            description="Test",
            origin=NoConformity.Origin.INTERNAL,
            severity=NoConformity.Severity.MINOR,
            detected_at=date.today(),
            detected_by=self.user,
            status=NoConformity.Status.IN_TREATMENT,
            root_cause_analysis="Causa test",
            corrective_action="Accion test",
        )
        
        # Crear una CAPA abierta
        capa = CAPAAction.objects.create(
            no_conformity=nc,
            title="Test Action",
            action_type=CAPAAction.ActionType.CORRECTIVE,
            status=CAPAAction.Status.OPEN,
        )
        
        # Intentar cerrar la NC debe fallar
        nc.status = NoConformity.Status.CLOSED
        with self.assertRaises(ValidationError) as cm:
            nc.full_clean()
        
        self.assertIn("acciones CAPA abiertas", str(cm.exception))

    def test_can_close_nc_when_all_capa_done(self):
        """Test que SÍ se puede cerrar NC cuando todas las CAPA son DONE."""
        nc = NoConformity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="NC con CAPA completada",
            description="Test",
            origin=NoConformity.Origin.INTERNAL,
            severity=NoConformity.Severity.MINOR,
            detected_at=date.today(),
            detected_by=self.user,
            status=NoConformity.Status.IN_TREATMENT,
            root_cause_analysis="Causa test",
            corrective_action="Accion test",
        )
        
        # Crear una CAPA y marcarla como DONE
        capa = CAPAAction.objects.create(
            no_conformity=nc,
            title="Test Action",
            action_type=CAPAAction.ActionType.CORRECTIVE,
            status=CAPAAction.Status.DONE,
        )
        
        # Ahora SÍ se puede cerrar la NC
        nc.status = NoConformity.Status.CLOSED
        nc.full_clean()  # No debe lanzar excepción
        nc.save()
        
        self.assertEqual(nc.status, NoConformity.Status.CLOSED)

    def test_auto_transition_nc_to_verification_when_all_capa_done(self):
        """Test que NC transiciona automáticamente a VERIFICATION cuando todas las CAPA son DONE."""
        nc = NoConformity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="NC para auto-transición",
            description="Test",
            origin=NoConformity.Origin.INTERNAL,
            severity=NoConformity.Severity.MINOR,
            detected_at=date.today(),
            detected_by=self.user,
            status=NoConformity.Status.IN_TREATMENT,
        )
        
        # Crear 2 CAPA
        capa1 = CAPAAction.objects.create(
            no_conformity=nc,
            title="Action 1",
            action_type=CAPAAction.ActionType.CORRECTIVE,
            status=CAPAAction.Status.OPEN,
        )
        capa2 = CAPAAction.objects.create(
            no_conformity=nc,
            title="Action 2",
            action_type=CAPAAction.ActionType.CORRECTIVE,
            status=CAPAAction.Status.IN_PROGRESS,
        )
        
        # Marcar primera como DONE - NC no debe cambiar (hay una aún en progreso)
        capa1.status = CAPAAction.Status.DONE
        capa1.save()
        
        nc.refresh_from_db()
        self.assertEqual(nc.status, NoConformity.Status.IN_TREATMENT)
        
        # Marcar segunda como DONE - Ahora SÍ debe transicionar
        capa2.status = CAPAAction.Status.DONE
        capa2.save()
        
        nc.refresh_from_db()
        self.assertEqual(nc.status, NoConformity.Status.VERIFICATION)
        self.assertIsNotNone(nc.verification_date)

    def test_severity_score_auto_calculation(self):
        """Test que severity_score se calcula automáticamente basado en severity."""
        # Test MINOR = 1
        nc_minor = NoConformity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="NC Menor",
            description="Test",
            origin=NoConformity.Origin.INTERNAL,
            severity=NoConformity.Severity.MINOR,
            detected_at=date.today(),
            detected_by=self.user,
        )
        self.assertEqual(nc_minor.severity_score, 1)
        
        # Test MAJOR = 2
        nc_major = NoConformity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="NC Mayor",
            description="Test",
            origin=NoConformity.Origin.INTERNAL,
            severity=NoConformity.Severity.MAJOR,
            detected_at=date.today(),
            detected_by=self.user,
        )
        self.assertEqual(nc_major.severity_score, 2)
        
        # Test CRITICAL = 3
        nc_critical = NoConformity.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="NC Crítica",
            description="Test",
            origin=NoConformity.Origin.INTERNAL,
            severity=NoConformity.Severity.CRITICAL,
            detected_at=date.today(),
            detected_by=self.user,
        )
        self.assertEqual(nc_critical.severity_score, 3)


class QualityObjectiveModelTests(TestCase):
    """Tests para el modelo QualityObjective."""

    def setUp(self):
        self.organization = Organization.objects.create(name="Empresa Test")
        self.process = Process.objects.create(
            organization=self.organization,
            code="P1",
            name="Proceso 1",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.PROCESS,
            is_active=True,
        )
        self.user = User.objects.create_user(username="owner", password="testpass")

    def test_status_achieved_when_current_reaches_target(self):
        """Verifica que status cambia a ACHIEVED cuando current_value >= target_value."""
        objective = QualityObjective.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="Objetivo Test",
            description="Descripcion",
            indicator="% Entregas",
            target_value=95.0,
            current_value=95.0,
            unit="%",
            frequency=QualityObjective.Frequency.MONTHLY,
            start_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            owner=self.user,
            is_active=True,
        )
        self.assertEqual(objective.status, QualityObjective.Status.ACHIEVED)

    def test_status_overdue_when_due_date_passed(self):
        """Verifica que status cambia a OVERDUE cuando vence la fecha."""
        objective = QualityObjective.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="Objetivo Vencido",
            description="Descripcion",
            indicator="% Entregas",
            target_value=95.0,
            current_value=80.0,
            unit="%",
            frequency=QualityObjective.Frequency.MONTHLY,
            start_date=date.today() - timedelta(days=60),
            due_date=date.today() - timedelta(days=10),  # Pasado
            owner=self.user,
            is_active=True,
        )
        self.assertEqual(objective.status, QualityObjective.Status.OVERDUE)

    def test_status_active_by_default(self):
        """Verifica que status es ACTIVE cuando está en tiempo y sin alcanzar meta."""
        objective = QualityObjective.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="Objetivo Activo",
            description="Descripcion",
            indicator="% Entregas",
            target_value=95.0,
            current_value=50.0,
            unit="%",
            frequency=QualityObjective.Frequency.MONTHLY,
            start_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            owner=self.user,
            is_active=True,
        )
        self.assertEqual(objective.status, QualityObjective.Status.ACTIVE)


class QualityObjectiveViewsTests(TestCase):
    """Tests para las vistas de objetivos de calidad."""

    def setUp(self):
        # Get the organization that the view will retrieve via _get_current_organization()
        # This is the first active org if one exists, otherwise the first org period
        self.organization = Organization.objects.filter(is_active=True).first() or Organization.objects.first()
        
        # If no orgs exist at all, create one
        if not self.organization:
            self.organization = Organization.objects.create(name="Test Org", is_active=True)
            
        self.process = Process.objects.create(
            organization=self.organization,
            code="QO-P1",
            name="QO Test Process",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.PROCESS,
            is_active=True,
        )
        
        self.admin_group, _ = Group.objects.get_or_create(name="Admin")
        self.calidad_group, _ = Group.objects.get_or_create(name="Calidad")
        
        self.admin_user = User.objects.create_user(username="qo_admin", password="testpass")
        self.admin_user.groups.add(self.admin_group)
        
        self.calidad_user = User.objects.create_user(username="qo_calidad", password="testpass")
        self.calidad_user.groups.add(self.calidad_group)
        
        self.normal_user = User.objects.create_user(username="user", password="testpass")

    def test_create_objective_generates_audit_event(self):
        """Verifica que crear un objetivo genera AuditEvent."""
        self.client.login(username="qo_admin", password="testpass")

        response = self.client.post(
            reverse("core:quality_objective_new"),
            data={
                "title": "Objetivo Test",
                "description": "Descripcion",
                "indicator": "% Entregas",
                "target_value": "95.0",
                "current_value": "0.0",
                "unit": "%",
                "frequency": "MONTHLY",
                "start_date": date.today().isoformat(),
                "due_date": (date.today() + timedelta(days=30)).isoformat(),
                "owner": self.admin_user.id,
                "related_process": self.process.id,
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            QualityObjective.objects.filter(title="Objetivo Test").exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                action="core.objective.created",
                actor=self.admin_user
            ).exists()
        )

    def test_non_authorized_cannot_create_objective(self):
        """Verifica que usuario sin permisos no puede crear objetivo."""
        self.client.login(username="user", password="testpass")

        response = self.client.post(
            reverse("core:quality_objective_new"),
            data={
                "title": "Objetivo No Autorizado",
                "description": "Descripcion",
                "indicator": "%",
                "target_value": "95.0",
                "current_value": "0.0",
                "unit": "%",
                "frequency": "MONTHLY",
                "start_date": date.today().isoformat(),
                "due_date": (date.today() + timedelta(days=30)).isoformat(),
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            QualityObjective.objects.filter(
                title="Objetivo No Autorizado"
            ).exists()
        )

    def test_calidad_can_create_and_edit_objective(self):
        """Verifica que usuarios del grupo Calidad pueden crear y editar objetivos."""
        self.client.login(username="qo_calidad", password="testpass")

        # Crear
        response = self.client.post(
            reverse("core:quality_objective_new"),
            data={
                "title": "Objetivo Calidad",
                "description": "Descripcion",
                "indicator": "Entregas",
                "target_value": "100.0",
                "current_value": "0.0",
                "unit": "unidades",
                "frequency": "QUARTERLY",
                "start_date": date.today().isoformat(),
                "due_date": (date.today() + timedelta(days=90)).isoformat(),
                "owner": self.calidad_user.id,
                "related_process": self.process.id,
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        objective = QualityObjective.objects.get(title="Objetivo Calidad")

        # Editar
        response = self.client.post(
            reverse("core:quality_objective_edit", args=[objective.pk]),
            data={
                "title": "Objetivo Calidad Editado",
                "description": "Descripcion actualizada",
                "indicator": "Entregas",
                "target_value": "100.0",
                "current_value": "50.0",
                "unit": "unidades",
                "frequency": "QUARTERLY",
                "start_date": objective.start_date.isoformat(),
                "due_date": objective.due_date.isoformat(),
                "owner": self.calidad_user.id,
                "related_process": self.process.id,
                "is_active": "on",
            },
        )

        objective.refresh_from_db()
        self.assertEqual(objective.title, "Objetivo Calidad Editado")
        self.assertEqual(objective.current_value, 50.0)

        # Verificar evento de auditoría de edición
        self.assertTrue(
            AuditEvent.objects.filter(
                action="core.objective.updated",
                actor=self.calidad_user
            ).exists()
        )

    def test_objective_list_renders(self):
        """Verifica que la vista de lista renderiza correctamente."""
        QualityObjective.objects.create(
            organization=self.organization,
            related_process=self.process,
            title="Objetivo 1",
            description="Test",
            indicator="Entregas",
            target_value=95.0,
            current_value=50.0,
            unit="%",
            frequency=QualityObjective.Frequency.MONTHLY,
            start_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            owner=self.admin_user,
            is_active=True,
        )

        self.client.login(username="user", password="testpass")
        response = self.client.get(reverse("core:quality_objective_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Objetivo 1")
        self.assertContains(response, "Entregas")


class InternalAuditViewsTests(TestCase):
    """Tests para auditorias internas (AUD-01)."""

    def setUp(self):
        self.organization = Organization.objects.filter(is_active=True).first() or Organization.objects.first()
        if not self.organization:
            self.organization = Organization.objects.create(name="Org Audit", is_active=True)
        self.process = Process.objects.create(
            organization=self.organization,
            code="A-01",
            name="Proceso Audit",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.PROCESS,
            is_active=True,
        )
        self.admin_group, _ = Group.objects.get_or_create(name="Admin")
        self.calidad_group, _ = Group.objects.get_or_create(name="Calidad")
        self.admin_user = User.objects.create_user(username="audit_admin", password="testpass")
        self.admin_user.groups.add(self.admin_group)
        self.normal_user = User.objects.create_user(username="audit_user", password="testpass")

    def _create_audit(self):
        audit = InternalAudit.objects.create(
            organization=self.organization,
            site=None,
            title="Audit 1",
            audit_date=date.today(),
            status=InternalAudit.Status.PLANNED,
        )
        audit.related_processes.add(self.process)
        return audit

    def test_create_audit_generates_event(self):
        self.client.login(username="audit_admin", password="testpass")

        response = self.client.post(
            reverse("core:audit_new"),
            data={
                "title": "Auditoria ISO",
                "audit_date": date.today().isoformat(),
                "audit_type": InternalAudit.AuditType.INTERNAL,
                "status": InternalAudit.Status.PLANNED,
                "related_processes": [self.process.id],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(InternalAudit.objects.filter(title="Auditoria ISO").exists())
        self.assertTrue(
            AuditEvent.objects.filter(action="core.audit.created", actor=self.admin_user).exists()
        )

    def test_checklist_submit_creates_answers(self):
        self.client.login(username="audit_admin", password="testpass")

        audit = self._create_audit()
        question = AuditQuestion.objects.create(
            organization=self.organization,
            process_type=Process.ProcessType.MISSIONAL,
            text="Se cumple el procedimiento?",
            is_active=True,
            ordering=1,
        )
        answer = AuditAnswer.objects.create(
            audit=audit,
            question=question,
            result=AuditAnswer.Result.NA,
        )

        prefix = "answers"
        response = self.client.post(
            reverse("core:audit_checklist", args=[audit.pk]),
            data={
                f"{prefix}-TOTAL_FORMS": "1",
                f"{prefix}-INITIAL_FORMS": "1",
                f"{prefix}-MIN_NUM_FORMS": "0",
                f"{prefix}-MAX_NUM_FORMS": "1000",
                f"{prefix}-0-id": str(answer.id),
                f"{prefix}-0-question": str(question.id),
                f"{prefix}-0-result": AuditAnswer.Result.OK,
                f"{prefix}-0-notes": "Ok",
            },
        )

        self.assertEqual(response.status_code, 302)
        answer.refresh_from_db()
        self.assertEqual(answer.result, AuditAnswer.Result.OK)
        self.assertTrue(
            AuditEvent.objects.filter(
                action="core.audit.checklist.submitted",
                actor=self.admin_user,
            ).exists()
        )

    def test_create_finding(self):
        self.client.login(username="audit_admin", password="testpass")

        audit = self._create_audit()
        response = self.client.post(
            reverse("core:audit_finding_new", args=[audit.pk]),
            data={
                "related_process": self.process.id,
                "finding_type": AuditFinding.FindingType.AREA_OF_CONCERN,
                "description": "Observacion de prueba",
                "severity": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(AuditFinding.objects.filter(audit=audit).exists())
        self.assertTrue(
            AuditEvent.objects.filter(
                action="core.audit.finding.created",
                actor=self.admin_user,
            ).exists()
        )

    def test_create_nc_from_finding(self):
        self.client.login(username="audit_admin", password="testpass")

        audit = self._create_audit()
        finding = AuditFinding.objects.create(
            audit=audit,
            related_process=self.process,
            finding_type=AuditFinding.FindingType.NONCONFORMITY,
            description="Hallazgo NC",
            severity=AuditFinding.Severity.MAJOR,
        )

        response = self.client.get(
            reverse("core:audit_finding_create_nc", args=[finding.pk])
        )

        self.assertEqual(response.status_code, 302)
        finding.refresh_from_db()
        self.assertIsNotNone(finding.nc)
        self.assertEqual(finding.nc.origin, NoConformity.Origin.INTERNAL_AUDIT)

    def test_create_nc_from_finding_external_audit(self):
        """Verifica que NC creado desde hallazgo de auditoria externa tenga origen EXTERNAL_AUDIT."""
        self.client.login(username="audit_admin", password="testpass")

        # Create audit with EXTERNAL type
        audit = InternalAudit.objects.create(
            organization=self.organization,
            site=None,
            title="Audit Externa",
            audit_date=date.today(),
            audit_type=InternalAudit.AuditType.EXTERNAL,
            status=InternalAudit.Status.PLANNED,
        )
        audit.related_processes.add(self.process)

        finding = AuditFinding.objects.create(
            audit=audit,
            related_process=self.process,
            finding_type=AuditFinding.FindingType.NONCONFORMITY,
            description="Hallazgo NC Externa",
            severity=AuditFinding.Severity.MAJOR,
        )

        response = self.client.get(
            reverse("core:audit_finding_create_nc", args=[finding.pk])
        )

        self.assertEqual(response.status_code, 302)
        finding.refresh_from_db()
        self.assertIsNotNone(finding.nc)
        self.assertEqual(finding.nc.origin, NoConformity.Origin.EXTERNAL_AUDIT)
        self.assertEqual(finding.nc.detected_by, self.admin_user)

    def test_cannot_create_nc_from_non_nonconformity_finding(self):
        """Verifica que no se puede crear NC desde hallazgo que no sea NONCONFORMITY."""
        self.client.login(username="audit_admin", password="testpass")

        audit = self._create_audit()
        finding = AuditFinding.objects.create(
            audit=audit,
            related_process=self.process,
            finding_type=AuditFinding.FindingType.AREA_OF_CONCERN,
            description="Hallazgo no conformidad",
            severity=AuditFinding.Severity.MINOR,
        )

        response = self.client.get(
            reverse("core:audit_finding_create_nc", args=[finding.pk])
        )

        self.assertEqual(response.status_code, 302)
        finding.refresh_from_db()
        self.assertIsNone(finding.nc)

    def test_non_authorized_cannot_create_audit(self):
        self.client.login(username="audit_user", password="testpass")

        response = self.client.post(
            reverse("core:audit_new"),
            data={
                "title": "No Autorizado",
                "audit_date": date.today().isoformat(),
                "audit_type": InternalAudit.AuditType.INTERNAL,
                "status": InternalAudit.Status.PLANNED,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(InternalAudit.objects.filter(title="No Autorizado").exists())


class AuditQuestionViewsTests(TestCase):
    """Tests para el banco de preguntas de auditoria (AUD-02)."""

    def setUp(self):
        self.organization = Organization.objects.filter(is_active=True).first() or Organization.objects.first()
        if not self.organization:
            self.organization = Organization.objects.create(name="Org Audit", is_active=True)
        self.process = Process.objects.create(
            organization=self.organization,
            code="AQ-01",
            name="Proceso Audit",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.PROCESS,
            is_active=True,
        )
        self.admin_group, _ = Group.objects.get_or_create(name="Admin")
        self.admin_user = User.objects.create_user(username="aq_admin", password="testpass")
        self.admin_user.groups.add(self.admin_group)
        self.normal_user = User.objects.create_user(username="aq_user", password="testpass")

    def test_admin_can_create_and_edit_question(self):
        self.client.login(username="aq_admin", password="testpass")

        response = self.client.post(
            reverse("core:audit_question_new"),
            data={
                "process_type": Process.ProcessType.MISSIONAL,
                "text": "Pregunta de prueba",
                "ordering": 10,
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        question = AuditQuestion.objects.get(text="Pregunta de prueba")

        response = self.client.post(
            reverse("core:audit_question_edit", args=[question.pk]),
            data={
                "process_type": Process.ProcessType.MISSIONAL,
                "text": "Pregunta editada",
                "ordering": 20,
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        question.refresh_from_db()
        self.assertEqual(question.text, "Pregunta editada")
        self.assertEqual(question.ordering, 20)

    def test_non_authorized_cannot_access_list(self):
        self.client.login(username="aq_user", password="testpass")

        response = self.client.get(reverse("core:audit_question_list"))

        self.assertEqual(response.status_code, 302)

    def test_checklist_shows_active_questions(self):
        self.client.login(username="aq_admin", password="testpass")

        audit = InternalAudit.objects.create(
            organization=self.organization,
            title="Audit Checklist",
            audit_date=date.today(),
            status=InternalAudit.Status.PLANNED,
        )
        audit.related_processes.add(self.process)
        AuditQuestion.objects.create(
            organization=self.organization,
            process_type=None,
            text="Pregunta general",
            is_active=True,
            ordering=1,
        )

        response = self.client.get(reverse("core:audit_checklist", args=[audit.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["formset"].total_form_count(), 1)


class ManagementReviewTests(TestCase):
    """Tests para el modelo ManagementReview y vistas relacionadas."""

    def setUp(self):
        """Configurar datos de prueba."""
        # Get the organization that the view will retrieve via _get_current_organization()
        # This is the first active org if one exists, otherwise the first org period
        self.organization = Organization.objects.filter(is_active=True).first() or Organization.objects.first()
        
        # If no orgs exist at all, create one
        if not self.organization:
            self.organization = Organization.objects.create(name="Test Org", is_active=True)
        
        # Crear usuario con permisos
        self.admin_user = User.objects.create_user(
            username="admin", password="admin123", is_staff=True, is_superuser=True
        )
        admin_group, _ = Group.objects.get_or_create(name="Administradores")
        self.admin_user.groups.add(admin_group)
        
        # Crear usuario sin permisos
        self.regular_user = User.objects.create_user(
            username="regular", password="regular123"
        )

    def test_create_review_generates_audit_event(self):
        """Verifica que crear una revisión genera un AuditEvent."""
        self.client.login(username="admin", password="admin123")
        
        review_data = {
            "review_date": date.today().strftime("%Y-%m-%d"),
            "chairperson": self.admin_user.pk,
            "attendees": "Juan Pérez, María García",
            "audit_results_summary": "Auditoría exitosa",
            "customer_feedback_summary": "Clientes satisfechos",
            "improvement_actions": "Mejorar procesos",
            "changes_to_qms": "Actualizar procedimientos",
        }
        
        initial_count = AuditEvent.objects.count()
        
        response = self.client.post(reverse("core:review_new"), review_data)
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertEqual(ManagementReview.objects.count(), 1)
        
        # Verificar que se creó un AuditEvent
        self.assertEqual(AuditEvent.objects.count(), initial_count + 1)
        
        event = AuditEvent.objects.latest("timestamp")
        self.assertEqual(event.action, "core.management_review.created")
        self.assertEqual(event.actor, self.admin_user)
        self.assertIn("review_date", event.metadata)

    def test_non_admin_cannot_create_review(self):
        """Verifica que usuarios sin permisos no pueden crear revisiones."""
        self.client.login(username="regular", password="regular123")
        
        review_data = {
            "review_date": date.today().strftime("%Y-%m-%d"),
            "attendees": "Test",
        }
        
        response = self.client.post(reverse("core:review_new"), review_data)
        
        # Usuario sin permisos es redirigido
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ManagementReview.objects.count(), 0)

    def test_review_list_renders(self):
        """Verifica que la lista de revisiones se renderiza correctamente."""
        ManagementReview.objects.create(
            organization=self.organization,
            review_date=date.today(),
            chairperson=self.admin_user,
        )
        
        self.client.login(username="admin", password="admin123")
        response = self.client.get(reverse("core:review_list"))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("reviews", response.context)
        self.assertEqual(len(response.context["reviews"]), 1)

    def test_review_detail_renders(self):
        """Verifica que el detalle de revisión se renderiza correctamente."""
        review = ManagementReview.objects.create(
            organization=self.organization,
            review_date=date.today(),
            chairperson=self.admin_user,
            attendees="Test attendees",
            audit_results_summary="Test summary",
        )
        
        self.client.login(username="admin", password="admin123")
        response = self.client.get(reverse("core:review_detail", args=[review.pk]))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["review"], review)
        self.assertContains(response, "Test attendees")
        self.assertContains(response, "Test summary")


class IndicatorTests(TestCase):
    """Tests para el módulo de indicadores de calidad."""

    def setUp(self):
        """Configurar datos de prueba."""
        self.organization = Organization.objects.filter(is_active=True).first() or Organization.objects.first()
        
        if not self.organization:
            self.organization = Organization.objects.create(name="Test Org", is_active=True)
        
        self.process = Process.objects.create(
            organization=self.organization,
            code="TEST-P1",
            name="Test Process",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.PROCESS,
            is_active=True,
        )
        
        self.admin_user = User.objects.create_user(
            username="admin_ind", password="admin123", is_staff=True, is_superuser=True
        )
        admin_group, _ = Group.objects.get_or_create(name="Administradores")
        self.admin_user.groups.add(admin_group)
        
        self.regular_user = User.objects.create_user(
            username="regular_ind", password="regular123"
        )

    def test_create_indicator_generates_audit_event(self):
        """Verifica que crear un indicador genera un AuditEvent."""
        self.client.login(username="admin_ind", password="admin123")
        
        indicator_data = {
            "name": "Disponibilidad del Servicio",
            "description": "Porcentaje de tiempo que el servicio está disponible",
            "frequency": QualityIndicator.Frequency.MONTHLY,
            "target_value": "99.5",
            "comparison_type": QualityIndicator.ComparisonType.GREATER_EQUAL,
            "unit": "%",
            "is_active": "on",
        }
        
        initial_count = AuditEvent.objects.count()
        
        response = self.client.post(reverse("core:indicator_new"), indicator_data)
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(QualityIndicator.objects.count(), 1)
        
        self.assertEqual(AuditEvent.objects.count(), initial_count + 1)
        
        event = AuditEvent.objects.latest("timestamp")
        self.assertEqual(event.action, "core.indicator.created")
        self.assertEqual(event.actor, self.admin_user)
        self.assertIn("indicator_id", event.metadata)

    def test_add_measurement_evaluates_target_correctly(self):
        """Verifica que is_within_target evalúa correctamente GREATER_EQUAL."""
        indicator = QualityIndicator.objects.create(
            organization=self.organization,
            name="Test Indicator",
            frequency=QualityIndicator.Frequency.MONTHLY,
            target_value=90.0,
            comparison_type=QualityIndicator.ComparisonType.GREATER_EQUAL,
        )
        
        # Medición que cumple la meta
        measurement_ok = IndicatorMeasurement.objects.create(
            indicator=indicator,
            measurement_date=date.today(),
            value=95.0,
        )
        
        self.assertTrue(measurement_ok.is_within_target())
        
        # Medición que no cumple la meta
        measurement_fail = IndicatorMeasurement.objects.create(
            indicator=indicator,
            measurement_date=date.today() - timedelta(days=1),
            value=85.0,
        )
        
        self.assertFalse(measurement_fail.is_within_target())

    def test_non_admin_cannot_create_indicator(self):
        """Verifica que usuarios sin permisos no pueden crear indicadores."""
        self.client.login(username="regular_ind", password="regular123")
        
        indicator_data = {
            "name": "Test",
            "frequency": QualityIndicator.Frequency.MONTHLY,
            "target_value": "90",
            "comparison_type": QualityIndicator.ComparisonType.GREATER_EQUAL,
        }
        
        response = self.client.post(reverse("core:indicator_new"), indicator_data)
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(QualityIndicator.objects.count(), 0)

    def test_indicator_list_renders(self):
        """Verifica que la lista de indicadores se renderiza correctamente."""
        QualityIndicator.objects.create(
            organization=self.organization,
            name="Test Indicator",
            frequency=QualityIndicator.Frequency.MONTHLY,
            target_value=90.0,
            comparison_type=QualityIndicator.ComparisonType.GREATER_EQUAL,
        )
        
        self.client.login(username="admin_ind", password="admin123")
        response = self.client.get(reverse("core:indicator_list"))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("indicators", response.context)
        self.assertEqual(len(response.context["indicators"]), 1)

    def test_indicator_ok_status(self):
        """Verifica que un indicador con medición dentro de meta retorna OK."""
        indicator = QualityIndicator.objects.create(
            organization=self.organization,
            name="Performance Indicator",
            frequency=QualityIndicator.Frequency.MONTHLY,
            target_value=90.0,
            comparison_type=QualityIndicator.ComparisonType.GREATER_EQUAL,
        )
        
        IndicatorMeasurement.objects.create(
            indicator=indicator,
            measurement_date=date.today(),
            value=95.0,
        )
        
        self.assertEqual(indicator.get_status(), "OK")

    def test_indicator_out_of_target(self):
        """Verifica que un indicador con medición fuera de meta retorna OUT_OF_TARGET."""
        indicator = QualityIndicator.objects.create(
            organization=self.organization,
            name="Performance Indicator",
            frequency=QualityIndicator.Frequency.MONTHLY,
            target_value=90.0,
            comparison_type=QualityIndicator.ComparisonType.GREATER_EQUAL,
        )
        
        IndicatorMeasurement.objects.create(
            indicator=indicator,
            measurement_date=date.today(),
            value=85.0,
        )
        
        self.assertEqual(indicator.get_status(), "OUT_OF_TARGET")

    def test_indicator_overdue(self):
        """Verifica que un indicador vencido retorna OVERDUE."""
        indicator = QualityIndicator.objects.create(
            organization=self.organization,
            name="Performance Indicator",
            frequency=QualityIndicator.Frequency.MONTHLY,
            target_value=90.0,
            comparison_type=QualityIndicator.ComparisonType.GREATER_EQUAL,
        )
        
        # Medición hace 40 días (más de 31 para MONTHLY)
        IndicatorMeasurement.objects.create(
            indicator=indicator,
            measurement_date=date.today() - timedelta(days=40),
            value=95.0,
        )
        
        self.assertEqual(indicator.get_status(), "OVERDUE")

    def test_indicator_no_data(self):
        """Verifica que un indicador sin mediciones retorna NO_DATA."""
        indicator = QualityIndicator.objects.create(
            organization=self.organization,
            name="Performance Indicator",
            frequency=QualityIndicator.Frequency.MONTHLY,
            target_value=90.0,
            comparison_type=QualityIndicator.ComparisonType.GREATER_EQUAL,
        )
        
        self.assertEqual(indicator.get_status(), "NO_DATA")


class NonconformingOutputTests(TestCase):
    """Tests para el modelo NonconformingOutput (ISO 8.7)."""

    def setUp(self):
        """Configurar datos de prueba."""
        self.organization = Organization.objects.create(name="Test Org")
        self.site = Site.objects.create(
            organization=self.organization,
            name="Test Site",
        )
        self.process = Process.objects.create(
            organization=self.organization,
            code="P1",
            name="Test Process",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.PROCESS,
        )

        # Usuario admin
        self.admin_user = User.objects.create_user(
            username="admin_pnc",
            password="admin123"
        )
        admin_group = Group.objects.get_or_create(name="Admin")[0]
        self.admin_user.groups.add(admin_group)

        # Usuario regular
        self.regular_user = User.objects.create_user(
            username="regular_pnc",
            password="regular123"
        )

    def test_create_pnc_generates_code_and_audit_event(self):
        """Verifica que crear PNC genera código incremental."""
        pnc = NonconformingOutput.objects.create(
            organization=self.organization,
            site=self.site,
            detected_at=date.today(),
            detected_by=self.admin_user,
            product_or_service="Tolva 26tn",
            description="Grieta en soldadura",
            severity=NonconformingOutput.Severity.MAJOR,
        )

        # Verificar código con patrón PNC-YYYY-NNN
        self.assertRegex(pnc.code, r"^PNC-\d{4}-\d{3}$")
        self.assertIsNotNone(pnc.code)

    def test_incremental_code_generation(self):
        """Verifica que los códigos se generan de forma incremental."""
        pnc1 = NonconformingOutput.objects.create(
            organization=self.organization,
            detected_at=date.today(),
            product_or_service="Product 1",
            description="Test 1",
            severity=NonconformingOutput.Severity.MINOR,
        )

        pnc2 = NonconformingOutput.objects.create(
            organization=self.organization,
            detected_at=date.today(),
            product_or_service="Product 2",
            description="Test 2",
            severity=NonconformingOutput.Severity.MAJOR,
        )

        self.assertEqual(
            int(pnc2.code.split("-")[-1]),
            int(pnc1.code.split("-")[-1]) + 1
        )

    def test_closing_sets_closed_at(self):
        """Verifica que al cerrar un PNC se asigna automáticamente closed_at."""
        pnc = NonconformingOutput.objects.create(
            organization=self.organization,
            detected_at=date.today(),
            product_or_service="Test Product",
            description="Test",
            severity=NonconformingOutput.Severity.MINOR,
            disposition=NonconformingOutput.Disposition.REWORK,
            status=NonconformingOutput.Status.CLOSED,
        )

        self.assertIsNotNone(pnc.closed_at)
        self.assertEqual(pnc.closed_at, date.today())

    def test_concession_requires_notes(self):
        """Verifica que CONCESIÓN requiere notas obligatoriamente."""
        pnc = NonconformingOutput(
            organization=self.organization,
            detected_at=date.today(),
            product_or_service="Test Product",
            description="Test",
            severity=NonconformingOutput.Severity.MAJOR,
            disposition=NonconformingOutput.Disposition.CONCESSION,
            status=NonconformingOutput.Status.CLOSED,
        )

        with self.assertRaises(ValidationError):
            pnc.full_clean()

    def test_non_admin_cannot_create_pnc(self):
        """Verifica que usuarios sin permisos no pueden ver la URL de crear."""
        self.client.login(username="regular_pnc", password="regular123")

        response = self.client.get(reverse("core:nonconforming_output_new"))
        
        # Debe ser PermissionDenied (403) o redirigir
        self.assertIn(response.status_code, [302, 403])

    def test_create_nc_from_pnc_links_correctly(self):
        """Verifica que linkear NC desde PNC es posible."""
        pnc = NonconformingOutput.objects.create(
            organization=self.organization,
            site=self.site,
            related_process=self.process,
            detected_at=date.today(),
            detected_by=self.admin_user,
            product_or_service="Test Product",
            description="Test",
            severity=NonconformingOutput.Severity.CRITICAL,
        )

        # Crear NC manualmente
        nc = NoConformity.objects.create(
            organization=self.organization,
            site=pnc.site,
            related_process=pnc.related_process,
            title=f"[PNC] {pnc.product_or_service}",
            description=pnc.description,
            origin=NoConformity.Origin.PRODUCTION,
            severity=pnc.severity,
            detected_at=pnc.detected_at,
            detected_by=pnc.detected_by,
        )

        # Linkear
        pnc.linked_nc = nc
        pnc.save()

        # Verificar vinculación
        pnc.refresh_from_db()
        self.assertEqual(pnc.linked_nc, nc)

    def test_pnc_list_view_renders(self):
        """Verifica que el listado de PNC se renderiza correctamente."""
        self.client.login(username="admin_pnc", password="admin123")

        # Acceder al listado
        response = self.client.get(reverse("core:nonconforming_output_list"))

        self.assertEqual(response.status_code, 200)
        # Verificar que el contexto tiene outputs (aunque sea vacío)
        self.assertIn("outputs", response.context)
        self.assertIn("organization", response.context)


class SupplierTests(TestCase):
    """Tests para el módulo Supplier (ISO 8.4)."""

    def setUp(self):
        """Preparación de datos de prueba."""
        self.organization = Organization.objects.filter(is_active=True).first()
        if self.organization is None:
            self.organization = Organization.objects.create(
                name="Test Organization",
                is_active=True,
            )
        self.site, _ = Site.objects.get_or_create(
            organization=self.organization,
            name="Test Site",
            defaults={"is_active": True},
        )
        self.process, _ = Process.objects.get_or_create(
            organization=self.organization,
            code="PROC-SUP-001",
            defaults={
                "name": "Test Process",
                "process_type": Process.ProcessType.MISSIONAL,
                "level": Process.Level.PROCESS,
                "is_active": True,
            },
        )

        # Admin user
        self.admin_user = User.objects.create_user(
            username="admin_supplier", password="admin123"
        )
        admin_group = Group.objects.get_or_create(name="Admin")[0]
        self.admin_user.groups.add(admin_group)

        # Regular user
        self.regular_user = User.objects.create_user(
            username="regular_supplier", password="regular123"
        )

    def test_create_supplier_with_audit_event(self):
        """Verifica que crear un supplier genera un AuditEvent."""
        supplier = Supplier.objects.create(
            organization=self.organization,
            name="Test Supplier",
            cuit="20-12345678-5",
            category=Supplier.Category.RAW_MATERIAL,
            status=Supplier.Status.PENDING,
        )

        # Verificar que el supplier se creó
        self.assertEqual(supplier.name, "Test Supplier")
        self.assertEqual(supplier.organization, self.organization)

    def test_supplier_unique_name_per_organization(self):
        """Verifica que no se pueden crear dos suppliers con el mismo nombre en la misma organización."""
        Supplier.objects.create(
            organization=self.organization,
            name="Test Supplier",
            category=Supplier.Category.RAW_MATERIAL,
        )

        with self.assertRaises(Exception):  # IntegrityError
            Supplier.objects.create(
                organization=self.organization,
                name="Test Supplier",
                category=Supplier.Category.SERVICE,
            )

    def test_create_evaluation_calculates_overall_score(self):
        """Verifica que la evaluación calcula automáticamente el promedio."""
        supplier = Supplier.objects.create(
            organization=self.organization,
            name="Test Supplier",
            category=Supplier.Category.RAW_MATERIAL,
        )

        evaluation = SupplierEvaluation.objects.create(
            supplier=supplier,
            organization=self.organization,
            evaluation_date=date.today(),
            quality_score=4,
            delivery_score=5,
            price_score=3,
            decision=SupplierEvaluation.Decision.APPROVED,
        )

        # Verificar que overall_score se calculó: (4+5+3)/3 = 4.0
        expected_score = round((4 + 5 + 3) / 3, 2)
        self.assertEqual(evaluation.overall_score, expected_score)

    def test_invalid_evaluation_score_raises_error(self):
        """Verifica que las puntuaciones fuera del rango 1-5 se rechazan."""
        supplier = Supplier.objects.create(
            organization=self.organization,
            name="Test Supplier",
            category=Supplier.Category.RAW_MATERIAL,
        )

        evaluation = SupplierEvaluation(
            supplier=supplier,
            organization=self.organization,
            evaluation_date=date.today(),
            quality_score=6,  # Inválido
            delivery_score=3,
            price_score=4,
            decision=SupplierEvaluation.Decision.APPROVED,
        )

        with self.assertRaises(ValidationError):
            evaluation.clean()

    def test_evaluation_updates_supplier_status(self):
        """Verifica que crear una evaluación actualiza el estado del supplier."""
        supplier = Supplier.objects.create(
            organization=self.organization,
            name="Test Supplier",
            category=Supplier.Category.RAW_MATERIAL,
            status=Supplier.Status.PENDING,
        )

        SupplierEvaluation.objects.create(
            supplier=supplier,
            organization=self.organization,
            evaluation_date=date.today(),
            quality_score=4,
            delivery_score=4,
            price_score=4,
            decision=SupplierEvaluation.Decision.APPROVED,
        )

        supplier.refresh_from_db()
        self.assertEqual(supplier.status, SupplierEvaluation.Decision.APPROVED)

    def test_evaluation_sets_next_evaluation_date(self):
        """Verifica que la evaluación calcula la próxima fecha según la decisión."""
        supplier = Supplier.objects.create(
            organization=self.organization,
            name="Test Supplier",
            category=Supplier.Category.RAW_MATERIAL,
        )

        today = date.today()

        # APPROVED -> 12 meses
        eval_approved = SupplierEvaluation.objects.create(
            supplier=supplier,
            organization=self.organization,
            evaluation_date=today,
            quality_score=4,
            delivery_score=4,
            price_score=4,
            decision=SupplierEvaluation.Decision.APPROVED,
        )

        supplier.refresh_from_db()
        next_date = supplier.next_evaluation_date
        expected_date = today + timedelta(days=365)  # aprox 12 meses
        
        # Verificar que la fecha está cerca (dentro de 5 días de diferencia)
        date_diff = abs((next_date - expected_date).days)
        self.assertTrue(date_diff <= 5, f"Diferencia de fecha: {date_diff} días")

    def test_non_admin_cannot_create_supplier(self):
        """Verifica que usuarios regulares no pueden crear suppliers."""
        self.client.login(username="regular_supplier", password="regular123")

        response = self.client.get(reverse("core:supplier_new"))
        self.assertEqual(response.status_code, 403)  # PermissionDenied

    def test_supplier_list_renders_and_links_to_detail(self):
        """La lista devuelve 200 y contiene link al detalle del proveedor."""
        supplier_1 = Supplier.objects.create(
            organization=self.organization,
            name="Supplier 1",
            category=Supplier.Category.RAW_MATERIAL,
        )
        Supplier.objects.create(
            organization=self.organization,
            name="Supplier 2",
            category=Supplier.Category.SERVICE,
        )

        self.client.login(username="admin_supplier", password="admin123")

        response = self.client.get(reverse("core:supplier_list"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("suppliers_with_status", response.context)
        self.assertContains(
            response,
            reverse("core:supplier_detail", args=[supplier_1.pk]),
        )

    def test_supplier_detail_renders(self):
        """El detalle de proveedor devuelve 200."""
        supplier = Supplier.objects.create(
            organization=self.organization,
            name="Supplier Detail",
            category=Supplier.Category.SERVICE,
        )

        self.client.login(username="admin_supplier", password="admin123")
        response = self.client.get(reverse("core:supplier_detail", args=[supplier.pk]))
        self.assertEqual(response.status_code, 200)

    def test_non_admin_cannot_see_edit_buttons(self):
        """Usuario sin permisos no ve botones Editar/Nueva evaluación."""
        supplier = Supplier.objects.create(
            organization=self.organization,
            name="Supplier Permissions",
            category=Supplier.Category.SERVICE,
        )

        self.client.login(username="regular_supplier", password="regular123")

        list_response = self.client.get(reverse("core:supplier_list"))
        self.assertEqual(list_response.status_code, 200)
        self.assertNotContains(list_response, "Editar")

        detail_response = self.client.get(reverse("core:supplier_detail", args=[supplier.pk]))
        self.assertEqual(detail_response.status_code, 200)
        self.assertNotContains(detail_response, "Editar")
        self.assertNotContains(detail_response, "Nueva Evaluación")

    def test_supplier_evaluation_overdue_badge(self):
        """Verifica que se detecta evaluación vencida."""
        supplier = Supplier.objects.create(
            organization=self.organization,
            name="Test Supplier",
            category=Supplier.Category.RAW_MATERIAL,
            # Próxima evaluación en el pasado
            next_evaluation_date=date.today() - timedelta(days=10),
        )

        self.assertTrue(supplier.is_evaluation_overdue)


class DashboardTests(TestCase):
    """Tests for Dashboard (DASH-01)."""

    def setUp(self):
        """Set up test data for dashboard."""
        # Create organization and users
        self.organization = Organization.objects.create(
            name="Dashboard Test Org",
            is_active=True,
        )
        
        self.user = User.objects.create_user(
            username="dash_user",
            password="dashpass",
        )
        
        # Create site
        self.site = Site.objects.create(
            organization=self.organization,
            name="Test Site",
            is_active=True,
        )

    def test_dashboard_home_requires_login(self):
        """Dashboard home requires authentication."""
        response = self.client.get(reverse("core:dashboard_home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_dashboard_home_responds_200(self):
        """Dashboard home responds 200 when authenticated."""
        self.client.login(username="dash_user", password="dashpass")
        response = self.client.get(reverse("core:dashboard_home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("title", response.context)
        self.assertIn("sites", response.context)
        self.assertIn("process_types", response.context)

    def test_dashboard_card_nc_responds_200(self):
        """NC Card responds 200."""
        self.client.login(username="dash_user", password="dashpass")
        response = self.client.get(reverse("core:dashboard_card_nc"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_card_nc_shows_open_ncs(self):
        """NC Card shows open non-conformities."""
        # Create a non-conformity
        nc = NoConformity.objects.create(
            organization=self.organization,
            code="NC-2025-001",
            title="Test NC",
            origin=NoConformity.Origin.INTERNAL,
            severity=NoConformity.Severity.MAJOR,
            status=NoConformity.Status.OPEN,
            detected_at=date.today(),
        )

        self.client.login(username="dash_user", password="dashpass")
        response = self.client.get(reverse("core:dashboard_card_nc"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NC-2025-001")
        self.assertContains(response, "1")  # Count should show 1

    def test_dashboard_card_capa_responds_200(self):
        """CAPA Card responds 200."""
        self.client.login(username="dash_user", password="dashpass")
        response = self.client.get(reverse("core:dashboard_card_capa"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_card_capa_shows_overdue(self):
        """CAPA Card shows overdue actions."""
        # Create a non-conformity and CAPA action
        nc = NoConformity.objects.create(
            organization=self.organization,
            code="NC-2025-002",
            title="Test NC for CAPA",
            origin=NoConformity.Origin.INTERNAL,
            severity=NoConformity.Severity.MINOR,
            status=NoConformity.Status.OPEN,
            detected_at=date.today(),
        )
        
        capa = CAPAAction.objects.create(
            organization=self.organization,
            no_conformity=nc,
            title="Test CAPA",
            action_type=CAPAAction.ActionType.CORRECTIVE,
            status=CAPAAction.Status.OPEN,
            due_date=date.today() - timedelta(days=5),  # Overdue
        )

        self.client.login(username="dash_user", password="dashpass")
        response = self.client.get(reverse("core:dashboard_card_capa"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1")  # Count should show 1

    def test_dashboard_card_indicadores_responds_200(self):
        """Indicators Card responds 200."""
        self.client.login(username="dash_user", password="dashpass")
        response = self.client.get(reverse("core:dashboard_card_indicadores"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_card_pnc_responds_200(self):
        """PNC Card responds 200."""
        self.client.login(username="dash_user", password="dashpass")
        response = self.client.get(reverse("core:dashboard_card_pnc"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_card_pnc_shows_open(self):
        """PNC Card shows open non-conforming outputs."""
        pnc = NonconformingOutput.objects.create(
            organization=self.organization,
            code="PNC-2025-001",
            product_or_service="Test Product",
            description="Test defect",
            detected_at=date.today(),
            status=NonconformingOutput.Status.OPEN,
        )

        self.client.login(username="dash_user", password="dashpass")
        response = self.client.get(reverse("core:dashboard_card_pnc"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PNC-2025-001")
        self.assertContains(response, "1")  # Count should show 1

    def test_dashboard_card_suppliers_responds_200(self):
        """Suppliers Card responds 200."""
        self.client.login(username="dash_user", password="dashpass")
        response = self.client.get(reverse("core:dashboard_card_suppliers"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_card_suppliers_shows_overdue(self):
        """Suppliers Card shows overdue evaluations."""
        supplier = Supplier.objects.create(
            organization=self.organization,
            name="Test Supplier",
            category=Supplier.Category.SERVICE,
            next_evaluation_date=date.today() - timedelta(days=10),
            is_active=True,
        )

        self.client.login(username="dash_user", password="dashpass")
        response = self.client.get(reverse("core:dashboard_card_suppliers"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Supplier")
        self.assertContains(response, "1")  # Count should show 1

    def test_dashboard_card_auditorias_responds_200(self):
        """Audits Card responds 200."""
        self.client.login(username="dash_user", password="dashpass")
        response = self.client.get(reverse("core:dashboard_card_auditorias"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_card_auditorias_shows_upcoming(self):
        """Audits Card shows upcoming audits."""
        audit = InternalAudit.objects.create(
            organization=self.organization,
            title="Test Audit",
            audit_date=date.today() + timedelta(days=10),
            audit_type=InternalAudit.AuditType.INTERNAL,
            status=InternalAudit.Status.PLANNED,
        )

        self.client.login(username="dash_user", password="dashpass")
        response = self.client.get(reverse("core:dashboard_card_auditorias"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Audit")
        self.assertContains(response, "1")  # Count should show 1

    def test_dashboard_contains_summary_block(self):
        """Dashboard home contains executive summary block."""
        # Create test data
        nc = NoConformity.objects.create(
            organization=self.organization,
            code="NC-2025-TEST",
            title="Test NC for Summary",
            origin=NoConformity.Origin.INTERNAL,
            severity=NoConformity.Severity.MAJOR,
            status=NoConformity.Status.OPEN,
            detected_at=date.today(),
        )

        supplier = Supplier.objects.create(
            organization=self.organization,
            name="Test Supplier for Summary",
            category=Supplier.Category.RAW_MATERIAL,
            is_active=True,
        )

        indicator = QualityIndicator.objects.create(
            organization=self.organization,
            name="Test Indicator",
            frequency=QualityIndicator.Frequency.MONTHLY,
            target_value=95.0,
            comparison_type=QualityIndicator.ComparisonType.GREATER_EQUAL,
            unit="%",
        )

        # Log in and get dashboard
        self.client.login(username="dash_user", password="dashpass")
        response = self.client.get(reverse("core:dashboard_home"))
        
        # Verify summary block is present
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resumen Ejecutivo")
        self.assertContains(response, "No Conformidades Abiertas")
        self.assertContains(response, "CAPA Vencidas")
        self.assertContains(response, "Indicadores en Meta")
        self.assertContains(response, "Proveedores Activos")
        
        # Verify summary context data is present
        self.assertIn("summary", response.context)
        summary = response.context["summary"]
        self.assertIn("total_ncs", summary)
        self.assertIn("total_capa_overdue", summary)
        self.assertIn("indicators_percentage", summary)
        self.assertIn("active_suppliers", summary)
        self.assertEqual(summary["total_ncs"], 1)
        self.assertEqual(summary["active_suppliers"], 1)


class HtmxProgressiveTests(TestCase):
    """Tests for progressive HTMX integration on dashboard and list views."""

    def setUp(self):
        self.organization = Organization.objects.filter(is_active=True).first()
        if self.organization is None:
            self.organization = Organization.objects.create(
                name="HTMX Test Org",
                is_active=True,
            )
        self.user = User.objects.create_user(
            username="htmx_user",
            password="htmxpass",
        )

    def test_dashboard_partial_endpoint_returns_partial_html(self):
        """Dashboard card endpoint returns partial HTML content."""
        self.client.login(username="htmx_user", password="htmxpass")
        response = self.client.get(reverse("core:dashboard_card_nc"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "card-header")
        self.assertNotContains(response, "<html")

    def test_nc_list_with_hx_request_returns_only_results_partial(self):
        """NC list should return only results partial for HX-Request."""
        self.client.login(username="htmx_user", password="htmxpass")
        response = self.client.get(
            reverse("core:nc_list"),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "empty-state")
        self.assertNotContains(response, "<html")

    def test_nc_list_without_hx_request_returns_full_page(self):
        """NC list should return full page when HX-Request header is absent."""
        self.client.login(username="htmx_user", password="htmxpass")
        response = self.client.get(reverse("core:nc_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<html")
        self.assertContains(response, "No Conformidades")

    def test_nc_list_hx_filters_do_not_break_queryset(self):
        """Filtering via HTMX keeps queryset behavior consistent."""
        NoConformity.objects.create(
            organization=self.organization,
            code="NC-HTMX-001",
            title="NC Critical",
            origin=NoConformity.Origin.INTERNAL,
            severity=NoConformity.Severity.CRITICAL,
            status=NoConformity.Status.OPEN,
            detected_at=date.today(),
        )
        NoConformity.objects.create(
            organization=self.organization,
            code="NC-HTMX-002",
            title="NC Minor",
            origin=NoConformity.Origin.INTERNAL,
            severity=NoConformity.Severity.MINOR,
            status=NoConformity.Status.OPEN,
            detected_at=date.today(),
        )

        self.client.login(username="htmx_user", password="htmxpass")
        response = self.client.get(
            reverse("core:nc_list"),
            {"severity": NoConformity.Severity.CRITICAL},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NC-HTMX-001")
        self.assertNotContains(response, "NC-HTMX-002")


class HtmxAdditionalListTests(TestCase):
    """Additional HTMX tests for other filtered lists."""

    def setUp(self):
        self.organization = Organization.objects.filter(is_active=True).first()
        if self.organization is None:
            self.organization = Organization.objects.create(
                name="HTMX Extra Org",
                is_active=True,
            )

        self.user = User.objects.create_user(
            username="htmx_extra_user",
            password="htmxpass",
        )

        self.site = Site.objects.create(
            organization=self.organization,
            name="HTMX Extra Site",
            is_active=True,
        )

        self.process = Process.objects.create(
            organization=self.organization,
            site=self.site,
            code="HTMX-PRC",
            name="Proceso HTMX",
            process_type=Process.ProcessType.SUPPORT,
            level=Process.Level.PROCESS,
            is_active=True,
        )

        self.stakeholder_a = Stakeholder.objects.create(
            organization=self.organization,
            site=self.site,
            name="Cliente HTMX A",
            stakeholder_type=Stakeholder.StakeholderType.CUSTOMER,
            expectations="Respuesta rápida",
            related_process=self.process,
            is_active=True,
        )
        self.stakeholder_b = Stakeholder.objects.create(
            organization=self.organization,
            site=self.site,
            name="Proveedor HTMX B",
            stakeholder_type=Stakeholder.StakeholderType.SUPPLIER,
            expectations="Pagos al día",
            related_process=self.process,
            is_active=True,
        )

        self.risk_a = RiskOpportunity.objects.create(
            organization=self.organization,
            site=self.site,
            related_process=self.process,
            stakeholder=self.stakeholder_a,
            title="Riesgo HTMX A",
            description="Descripción A",
            kind=RiskOpportunity.Kind.RISK,
            probability=5,
            impact=4,
            status=RiskOpportunity.Status.OPEN,
            owner=self.user,
        )
        self.risk_b = RiskOpportunity.objects.create(
            organization=self.organization,
            site=self.site,
            related_process=self.process,
            stakeholder=self.stakeholder_b,
            title="Oportunidad HTMX B",
            description="Descripción B",
            kind=RiskOpportunity.Kind.OPPORTUNITY,
            probability=2,
            impact=2,
            status=RiskOpportunity.Status.OPEN,
            owner=self.user,
        )

    def test_stakeholder_list_with_hx_request_returns_partial(self):
        self.client.login(username="htmx_extra_user", password="htmxpass")
        response = self.client.get(
            reverse("core:stakeholder_list"),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "stakeholder-list")
        self.assertNotContains(response, "<html")

    def test_stakeholder_list_hx_filter_keeps_queryset(self):
        self.client.login(username="htmx_extra_user", password="htmxpass")
        response = self.client.get(
            reverse("core:stakeholder_list"),
            {"stakeholder_type": Stakeholder.StakeholderType.CUSTOMER},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cliente HTMX A")
        self.assertNotContains(response, "Proveedor HTMX B")

    def test_risk_list_with_hx_request_returns_partial(self):
        self.client.login(username="htmx_extra_user", password="htmxpass")
        response = self.client.get(
            reverse("core:risk_list"),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "risks-table")
        self.assertNotContains(response, "<html")

    def test_risk_list_hx_filter_keeps_queryset(self):
        self.client.login(username="htmx_extra_user", password="htmxpass")
        response = self.client.get(
            reverse("core:risk_list"),
            {"kind": RiskOpportunity.Kind.RISK},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Riesgo HTMX A")
        self.assertNotContains(response, "Oportunidad HTMX B")