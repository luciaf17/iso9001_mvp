from django.urls import path

from apps.core.views import (
    context_detail,
    context_edit,
    risk_create,
    risk_dashboard,
    risk_detail,
    risk_edit,
    risk_list,
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
    path("risks/", risk_list, name="risk_list"),
    path("risks/dashboard/", risk_dashboard, name="risk_dashboard"),
    path("risks/new/", risk_create, name="risk_new"),
    path("risks/<int:pk>/", risk_detail, name="risk_detail"),
    path("risks/<int:pk>/edit/", risk_edit, name="risk_edit"),
]
