from django.test import TestCase
from django.contrib.auth.models import User
from .models import AuditEvent
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
        self.assertEqual(event.object_type, 'User')
        self.assertEqual(event.object_id, target_user.pk)
        self.assertEqual(event.metadata, metadata)
        self.assertIsNotNone(event.timestamp)
        
        # Verificar que se guardó en la base de datos
        self.assertEqual(AuditEvent.objects.count(), 1)
