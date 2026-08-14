"""URL ของรายงาน (mount ที่ /api/reports/)"""
from django.urls import path

from apps.reports.views import NoShowRateReportView, SummaryReportView

urlpatterns = [
    path("summary/", SummaryReportView.as_view(), name="report-summary"),
    path("no-show-rate/", NoShowRateReportView.as_view(), name="report-no-show-rate"),
]
