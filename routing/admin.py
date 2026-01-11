from django.contrib import admin
from .models import RoutingRule, DeskQueue

@admin.register(RoutingRule)
class RoutingRuleAdmin(admin.ModelAdmin):
    list_display = ('office', 'purpose', 'default_desk')
    list_filter = ('office',)

@admin.register(DeskQueue)
class DeskQueueAdmin(admin.ModelAdmin):
    list_display = ('visit', 'desk', 'assigned_at', 'is_active')
    list_filter = ('desk__office', 'desk', 'is_active')
    search_fields = ('visit__token',)
