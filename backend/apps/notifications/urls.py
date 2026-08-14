"""URL ของการแจ้งเตือน (mount ที่ /api/notifications/)"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.notifications.views import SMSLogViewSet

router = DefaultRouter()
router.register("sms-logs", SMSLogViewSet, basename="sms-log")

urlpatterns = [path("", include(router.urls))]
