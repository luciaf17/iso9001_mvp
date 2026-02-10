from django.urls import path

from apps.org.views import process_map

app_name = "org"

urlpatterns = [
    path("process-map/", process_map, name="process_map"),
]
