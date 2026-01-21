from django.urls import path
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', RedirectView.as_view(pattern_name='landing', permanent=False), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('management/', views.user_management, name='user_management'),
    
    # User URLs
    path('management/users/', views.UserListView.as_view(), name='user_list'),
    path('management/users/add/', views.UserCreateView.as_view(), name='user_create'),
    path('management/users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user_update'),
    path('management/users/<int:pk>/reset-password/', views.reset_password, name='user_reset_password'),

    # Password Change (Self-Service)
    path('password-change/', auth_views.PasswordChangeView.as_view(template_name='accounts/password_change.html', success_url='/accounts/password-change/done/'), name='password_change'),
    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='accounts/password_change_done.html'), name='password_change_done'),

    # Staff URLs
    path('management/staff/', views.StaffMemberListView.as_view(), name='staff_list'),
    path('management/staff/add/', views.StaffMemberCreateView.as_view(), name='staff_create'),
    path('management/staff/<int:pk>/edit/', views.StaffMemberUpdateView.as_view(), name='staff_update'),

    # Assignment URLs
    path('management/assignments/', views.UserAssignmentListView.as_view(), name='userassignment_list'),
    path('management/assignments/add/', views.UserAssignmentCreateView.as_view(), name='userassignment_create'),
    path('management/assignments/<int:pk>/edit/', views.UserAssignmentUpdateView.as_view(), name='userassignment_update'),

    # Log URLs
    path('management/logs/', views.LoginSessionListView.as_view(), name='loginsession_list'),

    # Office URLs
    path('management/offices/', views.OfficeListView.as_view(), name='office_list'),
    path('management/offices/add/', views.OfficeCreateView.as_view(), name='office_create'),
    path('management/offices/<int:pk>/edit/', views.OfficeUpdateView.as_view(), name='office_update'),

    # Desk URLs
    path('management/desks/', views.DeskListView.as_view(), name='desk_list'),
    path('management/desks/add/', views.DeskCreateView.as_view(), name='desk_create'),
    path('management/desks/<int:pk>/edit/', views.DeskUpdateView.as_view(), name='desk_update'),

    path('ajax/load-desks/', views.load_desks, name='ajax_load_desks'),
    path('whoami/', views.who_am_i, name='who_am_i'),
]
