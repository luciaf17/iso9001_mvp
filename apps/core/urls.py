from django.urls import path

from apps.core.views import context_detail, context_edit

app_name = "core"

urlpatterns = [
    path("context/", context_detail, name="context_detail"),
    path("context/edit/", context_edit, name="context_edit"),
]
