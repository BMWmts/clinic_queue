"""URL ของการนัดหมาย (mount ที่ /api/scheduling/)"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.scheduling.views import AppointmentViewSet, AvailableSlotsView

router = DefaultRouter()
router.register("appointments", AppointmentViewSet, basename="appointment")

urlpatterns = [
    path("available-slots/", AvailableSlotsView.as_view(), name="available-slots"),
    path("", include(router.urls)),
]
