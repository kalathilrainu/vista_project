from django.urls import path
from . import views

app_name = 'routing'

urlpatterns = [
    path('queue/', views.VisitQueueView.as_view(), name='visit_queue'),
    path('visit/update/<int:visit_id>/', views.EditVisitView.as_view(), name='update_visit'),
    path('desk/', views.DeskQueueView.as_view(), name='desk_queue'),
    path('attend/<int:visit_id>/', views.VisitAttendView.as_view(), name='attend_visit'),
    path('transfer/<int:visit_id>/', views.VisitTransferView.as_view(), name='transfer_visit'),
    path('complete/<int:visit_id>/', views.VisitCompleteView.as_view(), name='complete_visit'),
    path('vo/', views.VORoutingView.as_view(), name='vo_routing'),
    path('api/lock/<int:visit_id>/', views.LockVisitView.as_view(), name='lock_visit'),
    path('api/unlock/<int:visit_id>/', views.UnlockVisitView.as_view(), name='unlock_visit'),
    path('api/check-lock/<int:visit_id>/', views.CheckLockView.as_view(), name='check_lock'),
]
