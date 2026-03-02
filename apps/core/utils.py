def can_edit_context(user):
    if user is None:
        return False

    if getattr(user, "is_superuser", False):
        return True

    return user.groups.filter(name__in=["Admin", "Calidad"]).exists()


def can_edit_stakeholders(user):
    if user is None:
        return False

    if getattr(user, "is_superuser", False):
        return True

    return user.groups.filter(name__in=["Admin", "Calidad"]).exists()


def can_edit_risks(user):
    if user is None:
        return False

    if getattr(user, "is_superuser", False):
        return True

    return user.groups.filter(name__in=["Admin", "Calidad"]).exists()

def can_edit_nc(user):
    """Check if user can create/edit no conformities."""
    if user is None:
        return False

    if getattr(user, "is_superuser", False):
        return True

    return user.groups.filter(name__in=["Admin", "Calidad"]).exists()


def can_edit_objective(user):
    """Check if user can create/edit quality objectives."""
    if user is None:
        return False

    if getattr(user, "is_superuser", False):
        return True

    return user.groups.filter(name__in=["Admin", "Calidad"]).exists()


def can_edit_audit(user):
    """Check if user can create/edit internal audits."""
    if user is None:
        return False

    if getattr(user, "is_superuser", False):
        return True

    return user.groups.filter(name__in=["Admin", "Calidad"]).exists()


def can_edit_nonconforming_output(user):
    """Check if user can create/edit nonconforming outputs (ISO 8.7)."""
    if user is None:
        return False

    if getattr(user, "is_superuser", False):
        return True

    return user.groups.filter(name__in=["Admin", "Calidad"]).exists()


def can_edit_supplier(user):
    """Check if user can create/edit suppliers (ISO 8.4)."""
    if user is None:
        return False

    if getattr(user, "is_superuser", False):
        return True

    return user.groups.filter(name__in=["Admin", "Calidad"]).exists()