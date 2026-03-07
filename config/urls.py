from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.contrib import admin

from apps.core.views import home, LogoutAllowGetView

urlpatterns = [
    path("", home, name="home"),
    path("accounts/logout/", LogoutAllowGetView.as_view(), name="logout"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include(("apps.core.urls", "core"), namespace="core")),
    path("api/", include("apps.api.urls", namespace="api")),
    path("admin/", admin.site.urls),
    path("docs/", include("apps.docs.urls", namespace="docs")),
    path("org/", include(("apps.org.urls", "org"), namespace="org")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)