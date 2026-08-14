"""URL ของประเภทบริการ (mount ที่ /api/services/)"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.services.views import ServiceTypeViewSet

router = DefaultRouter()
router.register("", ServiceTypeViewSet, basename="service-type")

urlpatterns = [path("", include(router.urls))]
