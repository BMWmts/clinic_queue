"""
URL routing หลักของ backend

ทุก endpoint อยู่ใต้ /api/ และแยกตาม app (โดเมน) ให้ตรงกับโครงสร้างโปรเจกต์
"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/clinics/", include("apps.clinics.urls")),
    path("api/doctors/", include("apps.doctors.urls")),
    path("api/services/", include("apps.services.urls")),
    path("api/scheduling/", include("apps.scheduling.urls")),
    path("api/queue/", include("apps.queue.urls")),
    path("api/patients/", include("apps.patients.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    # OpenAPI schema — frontend ใช้ generate type ให้ตรงกับ backend
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
