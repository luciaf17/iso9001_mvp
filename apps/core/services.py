from .models import AuditEvent


def log_audit_event(*, actor, action, instance, metadata=None, object_type_override=None):
    """
    Registra un evento de auditoría.
    
    Args:
        actor: Usuario que ejecuta la acción (User instance o None)
        action: Descripción de la acción realizada
        instance: Instancia del modelo afectado (debe estar guardada)
        metadata: Diccionario con información adicional (opcional)
        object_type_override: Tipo de objeto personalizado (opcional)
    
    Returns:
        AuditEvent: El evento de auditoría creado
    
    Raises:
        ValueError: Si la instancia no tiene pk (no está guardada)
    """
    if instance.pk is None:
        raise ValueError("La instancia debe estar guardada en la base de datos (pk no puede ser None)")
    
    object_type = object_type_override or f'{instance._meta.app_label}.{instance.__class__.__name__}'
    object_id = instance.pk
    
    audit_event = AuditEvent.objects.create(
        actor=actor,
        action=action,
        object_type=object_type,
        object_id=object_id,
        metadata=metadata
    )
    
    return audit_event
