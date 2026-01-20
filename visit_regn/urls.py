from django.urls import path
from . import views

app_name = 'visit_regn'

urlpatterns = [
    # Visitor / Kiosk
    path('kiosk/', views.KioskHomeView.as_view(), name='kiosk_home'),
    path('register/qr/', views.QrRegisterView.as_view(), {'mode': 'QR'}, name='qr_register'),
    path('register/manual/', views.ManualRegisterView.as_view(), {'mode': 'KIOSK'}, name='manual_register'),
    path('register/quick/', views.QuickRegisterView.as_view(), name='quick_register'),
    
    path('token/<int:pk>/print/', views.TokenPrintView.as_view(), name='token_print'),

    # Mobile
    path('mobile-entry/', views.MobileEntryView.as_view(), name='mobile_entry'),
    path('mobile-token/<int:pk>/', views.MobileTokenView.as_view(), name='mobile_token'),
    path('visit/<int:pk>/download-token/', views.DownloadTokenView.as_view(), name='download_token'),

    # Staff
    path('staff/queue/', views.VisitQueueView.as_view(), name='visit_queue'),
    path('staff/visit/<int:pk>/', views.VisitDetailView.as_view(), name='visit_detail'),
]
