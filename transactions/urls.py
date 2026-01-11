from django.urls import path
from .views import TransactionCreateView, VisitorDisplayView, GetLatestCallsView

app_name = 'transactions'

urlpatterns = [
    path('process/<int:visit_id>/', TransactionCreateView.as_view(), name='process_transaction'),
    path('visitor-display/', VisitorDisplayView.as_view(), name='visitor_display'),
    path('api/latest-calls/', GetLatestCallsView.as_view(), name='get_latest_calls'),
]
