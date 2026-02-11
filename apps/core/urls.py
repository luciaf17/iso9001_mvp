from django.urls import path

from apps.core.views import (
    context_detail,
    context_edit,
    stakeholder_create,
    stakeholder_detail,
    stakeholder_edit,
    stakeholder_list,
)

app_name = "core"

urlpatterns = [
    path("context/", context_detail, name="context_detail"),
    path("context/edit/", context_edit, name="context_edit"),
    path("stakeholders/", stakeholder_list, name="stakeholder_list"),
    path("stakeholders/new/", stakeholder_create, name="stakeholder_new"),
    path("stakeholders/<int:pk>/", stakeholder_detail, name="stakeholder_detail"),
    path("stakeholders/<int:pk>/edit/", stakeholder_edit, name="stakeholder_edit"),
]
