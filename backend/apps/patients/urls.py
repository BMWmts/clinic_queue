"""URL ของฐานข้อมูลคนไข้ (mount ที่ /api/patients/)"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.patients.views import PatientViewSet

router = DefaultRouter()
router.register("", PatientViewSet, basename="patient")

urlpatterns = [path("", include(router.urls))]
