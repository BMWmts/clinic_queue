"""URL ของสาขา (mount ที่ /api/clinics/)"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.clinics.views import ClinicViewSet

router = DefaultRouter()
router.register("", ClinicViewSet, basename="clinic")

urlpatterns = [path("", include(router.urls))]
