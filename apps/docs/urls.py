from django.urls import path

from . import views

app_name = "docs"

urlpatterns = [
    path("", views.document_list, name="docs_list"),
    path("new/", views.document_create, name="docs_new"),
    path("<int:pk>/", views.document_detail, name="docs_detail"),
    path("<int:pk>/versions/new/", views.version_create, name="docs_version_new"),
    path("versions/<int:version_id>/approve/", views.version_approve, name="docs_version_approve"),
    path("<int:pk>/edit/", views.document_edit, name="docs_edit"),

]
