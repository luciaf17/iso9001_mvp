from django.urls import path

from apps.core.views import (
    context_detail,
    context_edit,
    capa_action_create,
    capa_action_edit,
    nc_create,
    nc_detail,
    nc_edit,
    nc_list,
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
    path("nc/", nc_list, name="nc_list"),
    path("nc/new/", nc_create, name="nc_new"),
    path("nc/<int:pk>/", nc_detail, name="nc_detail"),
    path("nc/<int:pk>/edit/", nc_edit, name="nc_edit"),
    path("nc/<int:nc_id>/actions/new/", capa_action_create, name="capa_action_create"),
    path("capa/<int:action_id>/edit/", capa_action_edit, name="capa_action_edit"),
]
