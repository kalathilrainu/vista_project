from django.db import models
from django.conf import settings
from django.utils import timezone
from accounts.models import Office, Desk
from visit_regn.models import Purpose, Visit

class VisitLock(models.Model):
    """
    Temporary lock on a visit to prevent concurrent editing/calling.
    """
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='active_lock')
    locked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    locked_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Lock on {self.visit.token} by {self.locked_by}"


class RoutingRule(models.Model):
    """
    Maps (Office, Purpose) -> Default Desk for auto-routing.
    """
    office = models.ForeignKey(Office, on_delete=models.CASCADE, related_name='routing_rules')
    purpose = models.ForeignKey(Purpose, on_delete=models.CASCADE, related_name='routing_rules')
    default_desk = models.ForeignKey(Desk, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('office', 'purpose')
        verbose_name = "Routing Rule"
        verbose_name_plural = "Routing Rules"

    def __str__(self):
        return f"{self.office.name} - {self.purpose.name} -> {self.default_desk.name}"

class DeskQueue(models.Model):
    """
    Active assignment of a visit to a desk.
    Acts as the 'current holder' of the token.
    """
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='desk_queue')
    desk = models.ForeignKey(Desk, on_delete=models.CASCADE, related_name='queue_items')
    
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['assigned_at'] # FIFO
        verbose_name = "Desk Queue Item"
        verbose_name_plural = "Desk Queue Items"

    def __str__(self):
        return f"{self.visit.token} @ {self.desk.name}"
