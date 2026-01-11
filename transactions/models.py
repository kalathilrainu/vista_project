from django.db import models
from django.conf import settings
from visit_regn.models import Visit

class Transaction(models.Model):
    """
    Stores details of the transaction processed by the staff.
    """
    STATUS_CHOICES = [
        ('IN_PROGRESS', 'In Progress'),
        ('CLOSED', 'Closed'),
        ('OPEN_FILE', 'Open File'), # For Filing Module transition
    ]

    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='transaction')
    # tp_number: Thandaper Number / Landholder ID. Manual entry.
    tp_number = models.CharField(max_length=5, blank=True, null=True, help_text="Thandaper Number / Landholder ID")
    # block: Block identifier to disambiguate tp_number
    block = models.CharField(max_length=4, blank=True, null=True, help_text="Block Identifier (e.g. Blk1)")
    
    remarks1 = models.CharField(max_length=255, blank=True, null=True)
    remarks2 = models.CharField(max_length=255, blank=True, null=True)
    remarks3 = models.CharField(max_length=255, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_PROGRESS')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Transaction for {self.visit.token} - {self.tp_number or 'No TP'}"
