"""URL ของหน้าจอคิว (mount ที่ /api/queue/)"""
from django.urls import path

from apps.queue.views import (
    AppointmentRescheduleView,
    AppointmentStatusUpdateView,
    TodayQueueView,
    WalkInView,
)

urlpatterns = [
    path("today/", TodayQueueView.as_view(), name="queue-today"),
    path("walk-in/", WalkInView.as_view(), name="queue-walk-in"),
    path(
        "appointments/<int:appointment_id>/status/",
        AppointmentStatusUpdateView.as_view(),
        name="queue-appointment-status",
    ),
    path(
        "appointments/<int:appointment_id>/reschedule/",
        AppointmentRescheduleView.as_view(),
        name="queue-appointment-reschedule",
    ),
]
