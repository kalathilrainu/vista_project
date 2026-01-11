from django.urls import path
from . import views

app_name = 'mis'

urlpatterns = [
    path('', views.MISDashboardView.as_view(), name='dashboard'),
    path('daily/', views.DailyReportView.as_view(), name='daily_report'),
    path('files/', views.FileStatusReportView.as_view(), name='file_report'),
    path('analysis/aging/', views.AgingAnalysisView.as_view(), name='aging_report'),
    path('analysis/service/', views.ServiceAnalysisView.as_view(), name='service_report'),
]
