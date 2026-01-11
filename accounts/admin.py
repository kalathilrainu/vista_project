from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, StaffMember, UserAssignment, LoginSession

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'office', 'desk', 'is_active', 'is_staff')
    list_filter = ('role', 'office', 'is_active', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Office Assignment', {'fields': ('office', 'role', 'desk')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Office Assignment', {'fields': ('office', 'role', 'desk')}),
    )

@admin.register(User)
class UserAdminConfig(CustomUserAdmin):
    pass

@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ('pen', 'name', 'designation', 'office', 'is_active')
    list_filter = ('office', 'designation', 'is_active')
    search_fields = ('name', 'pen')

@admin.register(UserAssignment)
class UserAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'staff_member', 'from_date', 'to_date', 'is_active')
    list_filter = ('from_date', 'to_date')
    search_fields = ('user__username', 'staff_member__name')

@admin.register(LoginSession)
class LoginSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'staff_member', 'login_time', 'logout_time', 'ip_address')
    list_filter = ('login_time', 'logout_time')
    search_fields = ('user__username', 'staff_member__name', 'ip_address')

from .models import District, Taluk, Office, Desk

@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')

@admin.register(Taluk)
class TalukAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'district')
    list_filter = ('district',)
    search_fields = ('name', 'code')

@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'taluk', 'is_headquarters')
    list_filter = ('taluk__district', 'taluk')
    search_fields = ('name', 'code')
    autocomplete_fields = ['taluk']

@admin.register(Desk)
class DeskAdmin(admin.ModelAdmin):
    list_display = ('name', 'office')
    list_filter = ('office',)
    search_fields = ('name', 'office__name')
