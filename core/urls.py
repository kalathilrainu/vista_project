from django.urls import path
from accounts.views import LandingLoginView
from . import views

urlpatterns = [
    path('', LandingLoginView.as_view(), name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('track/', views.track_status, name='track_status'),

]
