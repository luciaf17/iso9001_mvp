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
)
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