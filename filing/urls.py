from django.urls import path
from . import views

app_name = 'filing'

urlpatterns = [
    path('file/create/<int:visit_id>/', views.FileCreateView.as_view(), name='file_create'),
    path('file/<int:file_id>/', views.FileDetailView.as_view(), name='file_detail'),
    
    # API
    path('api/check_status/', views.CheckFileStatusView.as_view(), name='check_file_status'),
    path('list/', views.FileListView.as_view(), name='file_list'),
]
