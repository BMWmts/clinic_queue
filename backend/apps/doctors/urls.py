"""URL ของแพทย์/ตารางออกตรวจ/ช่วงเวลาที่ถูกบล็อก (mount ที่ /api/doctors/)"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.doctors.views import DoctorScheduleViewSet, DoctorViewSet, TimeBlockViewSet

router = DefaultRouter()
router.register("schedules", DoctorScheduleViewSet, basename="doctor-schedule")
router.register("time-blocks", TimeBlockViewSet, basename="time-block")
# ลงทะเบียนเส้นทางว่างไว้ท้ายสุด เพื่อไม่ให้ทับ path ของ schedules/time-blocks
router.register("", DoctorViewSet, basename="doctor")

urlpatterns = [path("", include(router.urls))]
