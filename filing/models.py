from django.db import models
from visit_regn.models import Visit
from accounts.models import Desk, User, Office
from django.utils import timezone
from django.db import transaction

class OfficeFile(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Pending'),
        ('CLOSED', 'Closed'),
    ]

    INTERIM_STATUS_CHOICES = [
        ('Processing', 'Processing'),
        ('Site Visit Required', 'Site Visit Required'),
        ('Addl Documents Awaited', 'Addl Documents Awaited'),
        ('Payment Pending', 'Payment Pending'),
        ('Sent for external verification report', 'Sent for external verification report'),
        ('Closed', 'Closed'),
    ]

    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='office_file')
    office = models.ForeignKey(Office, on_delete=models.CASCADE, related_name='office_files', null=True, blank=True)
    
    file_number = models.CharField(max_length=50, blank=True, help_text="Auto-generated File Number (Serial/Year)")
    year = models.PositiveIntegerField(null=True, blank=True)
    serial_number = models.PositiveIntegerField(null=True, blank=True)
    
    desk = models.ForeignKey(Desk, on_delete=models.SET_NULL, null=True, blank=True, related_name='office_files')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    interim_status = models.CharField(max_length=50, choices=INTERIM_STATUS_CHOICES, default='Processing')
    
    fee_receipt_no = models.CharField(max_length=50, blank=True, null=True)
    fee_receipt_date = models.DateField(blank=True, null=True)
    
    REPLY_TYPE_CHOICES = [
        ('Certificate', 'Certificate'),
        ('Report', 'Report'),
        ('Statement of Facts', 'Statement of Facts'),
        ('Mozhi', 'Mozhi'),
        ('Other', 'Other'),
    ]

    DESPATCH_MODE_CHOICES = [
        ('By Hand', 'By Hand'),
        ('By Post', 'By Post'),
        ('eOffice', 'eOffice'),
        ('eDistrict', 'eDistrict'),
        ('Other', 'Other'),
    ]

    reply_to = models.CharField(max_length=255, blank=True, null=True)
    reply_date = models.DateField(blank=True, null=True)
    
    reply_type = models.CharField(max_length=50, choices=REPLY_TYPE_CHOICES, blank=True, null=True)
    despatch_mode = models.CharField(max_length=50, choices=DESPATCH_MODE_CHOICES, blank=True, null=True)
    despatch_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="Despatch ID / Memo No")
    
    remarks1 = models.CharField(max_length=255, blank=True, null=True)
    remarks2 = models.CharField(max_length=255, blank=True, null=True)
    remarks3 = models.CharField(max_length=255, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('office', 'year', 'serial_number')

    def save(self, *args, **kwargs):
        if not self.office and self.visit:
             self.office = self.visit.office
             
        if not self.file_number:
            now = timezone.localtime()
            current_year = now.year
            
            with transaction.atomic():
                # Lock the table or just filter carefully. 
                # Ideally selection for update to avoid race conditions but for low volume this is okay?
                # Let's use select_for_update on a queryset if possible, but finding "last" is safer.
                
                # Check for existing highest serial for this office & year
                last_file = OfficeFile.objects.filter(
                    office=self.office, 
                    year=current_year
                ).order_by('serial_number').last()
                
                next_serial = (last_file.serial_number + 1) if last_file and last_file.serial_number else 1
                
                self.year = current_year
                self.serial_number = next_serial
                self.file_number = f"{self.serial_number}/{self.year}"
                
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"File {self.file_number} (Visit: {self.visit.token})"

class DocumentSubmission(models.Model):
    office_file = models.ForeignKey(OfficeFile, on_delete=models.CASCADE, related_name='document_submissions')
    submitted_at = models.DateTimeField(auto_now_add=True)
    papers_submitted = models.TextField(help_text="Details of papers/documents submitted")
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Docs for {self.office_file.file_number} at {self.submitted_at}"
