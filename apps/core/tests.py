from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import AuditEvent, Organization, Process
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
