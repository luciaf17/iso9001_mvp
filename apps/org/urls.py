from django.urls import path

from apps.org.views import (
    process_create_child,
    process_create_level1,
    process_deactivate,
    process_edit,
    process_map,
)

app_name = "org"

urlpatterns = [
    path("process-map/", process_map, name="process_map"),
    path("processes/new/", process_create_level1, name="process_new"),
    path("processes/<int:parent_id>/children/new/", process_create_child, name="process_child_new"),
    path("processes/<int:process_id>/edit/", process_edit, name="process_edit"),
    path("processes/<int:process_id>/deactivate/", process_deactivate, name="process_deactivate"),
]
