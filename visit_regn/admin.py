from django.contrib import admin
from .models import Visit, VisitLog, DailyTokenCounter, Purpose

@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('token', 'office', 'name', 'mobile', 'purpose', 'status', 'token_issue_time', 'current_desk')
    list_filter = ('office', 'status', 'registration_mode', 'token_issue_time')
    search_fields = ('token', 'mobile', 'name', 'reference_number')
    readonly_fields = ('token', 'token_issue_time', 'created_by')

@admin.register(VisitLog)
class VisitLogAdmin(admin.ModelAdmin):
    list_display = ('visit', 'action', 'by_user', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('visit__token', 'remarks')

@admin.register(DailyTokenCounter)
class DailyTokenCounterAdmin(admin.ModelAdmin):
    list_display = ('office', 'date', 'last_seq')
    list_filter = ('date', 'office')

@admin.register(Purpose)
class PurposeAdmin(admin.ModelAdmin):
    list_display = ('name',)
