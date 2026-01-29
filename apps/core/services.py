from .models import AuditEvent


def log_audit_event(*, actor, action, instance, metadata=None):
    """
    Registra un evento de auditoría.
    
    Args:
        actor: Usuario que ejecuta la acción (User instance o None)
        action: Descripción de la acción realizada
        instance: Instancia del modelo afectado
        metadata: Diccionario con información adicional (opcional)
    
    Returns:
        AuditEvent: El evento de auditoría creado
    """
    object_type = instance.__class__.__name__
    object_id = instance.pk
    
    audit_event = AuditEvent.objects.create(
        actor=actor,
        action=action,
        object_type=object_type,
        object_id=object_id,
        metadata=metadata
    )
    
    return audit_event
