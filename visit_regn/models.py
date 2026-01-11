from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.utils.translation import gettext_lazy as _


# Using accounts.Office/Desk as discovered in codebase
from accounts.models import Office, Desk, StaffMember

class Purpose(models.Model):
    name = models.CharField(max_length=100)
    # Placeholder for Malayalam translation
    # name_ml = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return self.name

class DailyTokenCounter(models.Model):
    office = models.ForeignKey(Office, on_delete=models.CASCADE)
    date = models.DateField()
    last_seq = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('office', 'date')

class Visit(models.Model):
    class RegistrationMode(models.TextChoices):
        QR = 'QR', 'QR Code'
        KIOSK = 'KIOSK', 'Kiosk'
        QUICK = 'QUICK', 'Quick'

    class Status(models.TextChoices):
        WAITING = 'WAITING', 'Waiting'
        ROUTED = 'ROUTED', 'Routed'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    office = models.ForeignKey(Office, on_delete=models.CASCADE, related_name='visits')
    token = models.CharField(max_length=20) # Format: OFFICECODE-YYYYMMDD-NNN
    mobile = models.CharField(max_length=15, null=True, blank=True)
    name = models.CharField(max_length=150, null=True, blank=True)
    purpose = models.ForeignKey(Purpose, on_delete=models.PROTECT)
    reference_number = models.CharField(max_length=50, null=True, blank=True)
    registration_mode = models.CharField(max_length=10, choices=RegistrationMode.choices)
    
    token_issue_time = models.DateTimeField(auto_now_add=True)
    token_attend_time = models.DateTimeField(null=True, blank=True)
    
    current_desk = models.ForeignKey(Desk, on_delete=models.SET_NULL, null=True, blank=True, related_name='current_visits')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.WAITING)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_visits') # Default VISITOR handled in view/method
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Link to an existing office file (for repeat visits)
    related_office_file = models.ForeignKey('filing.OfficeFile', on_delete=models.SET_NULL, null=True, blank=True, related_name='related_visits')

    class Meta:
        indexes = [
            models.Index(fields=['office', 'token']),
            models.Index(fields=['office', 'token_issue_time']),
        ]
        unique_together = ('office', 'token') # Token unique per office (and effectively day due to format)

    @property
    def formatted_issue_time(self):
        if not self.token_issue_time:
            return ""
        return timezone.localtime(self.token_issue_time).strftime("%d %b %Y, %I:%M %p")

    def __str__(self):
        return f"{self.token} - {self.name or 'Visitor'}"

    @classmethod
    def generate_token(cls, office):
        today = timezone.localtime().date()
        
        with transaction.atomic():
            counter, created = DailyTokenCounter.objects.select_for_update().get_or_create(
                office=office,
                date=today,
                defaults={'last_seq': 0}
            )
            counter.last_seq += 1
            counter.save()
            
            # Token format: <OFFICECODE>-<YYYYMMDD>-<NNN>
            # Assuming office.code exists and is consistent
            date_str = today.strftime('%Y%m%d')
            seq_str = f"{counter.last_seq:03d}"
            token = f"{office.code}-{date_str}-{seq_str}"
            
            return token

    @classmethod
    def create_from_kiosk(cls, data, office, user=None, mode='KIOSK'):
        from . import services
        
        # 'user' should be passed, typically the 'VISITOR' user
        if not user:
             # Fallback if not provided, though views should provide it
             pass

        token = cls.generate_token(office)
        
        visit = cls(
            office=office,
            token=token,
            mobile=data.get('mobile'),
            name=data.get('name'),
            purpose=data.get('purpose'), # Expecting Purpose instance
            reference_number=data.get('reference_number'),
            registration_mode=mode,
            created_by=user,
            status=cls.Status.WAITING
        )
        visit.save()

        # Log CREATED
        services.log_visit_action(visit, 'CREATED', by_user=user, remarks=f"Registered via {mode}")

        # Attempt Routing
        try:
             services.route_visit_stub(visit) # Using our stub/wrapper which handles import 
        except Exception as e:
             services.log_visit_action(visit, 'COMMENT', by_user=user, remarks=f"Routing failed: {str(e)}")

        return visit


class VisitLog(models.Model):
    class Action(models.TextChoices):
        CREATED = 'CREATED', 'Created'
        ROUTED = 'ROUTED', 'Routed'
        ASSIGNED = 'ASSIGNED', 'Assigned' # Desk Assigned
        ATTENDED = 'ATTENDED', 'Attended'
        TRANSFERRED = 'TRANSFERRED', 'Transferred'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        COMMENT = 'COMMENT', 'Comment'

    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=20, choices=Action.choices)
    
    by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    by_staff = models.ForeignKey(StaffMember, on_delete=models.SET_NULL, null=True, blank=True)
    
    from_desk = models.ForeignKey(Desk, on_delete=models.SET_NULL, null=True, blank=True, related_name='transfers_from')
    to_desk = models.ForeignKey(Desk, on_delete=models.SET_NULL, null=True, blank=True, related_name='transfers_to')
    
    remarks = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.visit.token} - {self.action}"
