from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from . import views

app_name = "api"

urlpatterns = [
    path("token/", obtain_auth_token, name="api_token"),
    path("health/", views.api_health, name="api_health"),
    path("processes/", views.ProcessListView.as_view(), name="process_list"),
    path("users/", views.UserListView.as_view(), name="user_list"),
    path("nc/", views.NCListView.as_view(), name="nc_list"),
    path("nc/create/", views.NCCreateView.as_view(), name="nc_create"),
    path("nc/<int:pk>/", views.NCDetailView.as_view(), name="nc_detail"),
    path("pnc/", views.PNCListView.as_view(), name="api_pnc_list"),
    path("pnc/create/", views.PNCCreateView.as_view(), name="api_pnc_create"),
    path("pnc/<int:pk>/", views.PNCDetailView.as_view(), name="api_pnc_detail"),
    path("interaction/", views.InteractionListView.as_view(), name="api_interaction_list"),
    path("interaction/create/", views.InteractionCreateView.as_view(), name="api_interaction_create"),
    path("interaction/<int:pk>/", views.InteractionDetailView.as_view(), name="api_interaction_detail"),
    path("capa/create/", views.CAPACreateView.as_view(), name="capa_create"),
]
