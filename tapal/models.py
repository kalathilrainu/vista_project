from django.db import models
from django.conf import settings

class Tapal(models.Model):
    class Type(models.TextChoices):
        GOVT = "GOVT", "Government Order"
        PUBLIC = "PUBLIC", "Public Petition"
        COURT = "COURT", "Court Case"
        INTERNAL = "INTERNAL", "Internal Memo"

    sender = models.CharField(max_length=150)
    subject = models.CharField(max_length=250)
    tapal_type = models.CharField(max_length=20, choices=Type.choices, default=Type.PUBLIC)
    received_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_closed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.subject} ({self.sender})"

class TapalMovement(models.Model):
    tapal = models.ForeignKey(Tapal, on_delete=models.CASCADE, related_name="movements")
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="sent_tapals")
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="received_tapals")
    note = models.TextField(blank=True)
    moved_at = models.DateTimeField(auto_now_add=True)
