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
