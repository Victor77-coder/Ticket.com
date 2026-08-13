from django.contrib import admin
from django.urls import include, path

from config.health import healthz

urlpatterns = [
    path("healthz", healthz),
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.catalog.urls")),
    path("api/v1/", include("apps.screening.urls")),
    path("api/v1/auth/", include("apps.accounts.urls")),
]
