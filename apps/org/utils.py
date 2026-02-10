def can_edit_processes(user):
    if user is None:
        return False

    if getattr(user, "is_superuser", False):
        return True

    return user.groups.filter(name__in=["Admin", "Calidad"]).exists()
