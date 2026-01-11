from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class District(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True, help_text="e.g. 05")
    
    def __str__(self):
        return f"{self.name} ({self.code})"

class Taluk(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True, help_text="e.g. 0503")
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='taluks')
    
    def __str__(self):
        return f"{self.name} ({self.code})"

class Office(models.Model):
    name = models.CharField(max_length=100, help_text="Village Name, e.g. Nattakam")
    code = models.CharField(max_length=20, unique=True, help_text="e.g. 050317")
    taluk = models.ForeignKey(Taluk, on_delete=models.SET_NULL, null=True, blank=True, related_name='offices')
    is_headquarters = models.BooleanField(default=False, help_text="Is this the Taluk Headquarters?")
    
    def __str__(self):
        return f"{self.name} ({self.code})"

class Desk(models.Model):
    name = models.CharField(max_length=100)
    office = models.ForeignKey(Office, on_delete=models.CASCADE, related_name='desks')
    
    def __str__(self):
        return self.name

class User(AbstractUser):
    class Role(models.TextChoices):
        VO = 'VO', 'Village Officer'
        SVO = 'SVO', 'Special Village Officer'
        VA = 'VA', 'Village Assistant'
        VFA = 'VFA', 'Village Field Assistant'
        CLERK = 'CLERK', 'Clerk'
        ADMIN = 'ADMIN', 'Admin'
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'

    office = models.ForeignKey(Office, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    desk = models.ForeignKey(Desk, on_delete=models.SET_NULL, null=True, blank=True)
    # is_active is already in AbstractUser, but we can override or leave it. 
    # Requirement says "is_active (default=True)". AbstractUser has it default=True.
    
    def __str__(self):
        return self.username

    def get_current_staff_name(self):
        from .utils import get_current_staff_for_user
        staff = get_current_staff_for_user(self)
        if staff:
            return staff.name
        return None

class StaffMember(models.Model):
    pen = models.CharField(max_length=50, unique=True, verbose_name="Permanent Employee Number")
    name = models.CharField(max_length=150)
    designation = models.CharField(max_length=100)
    office = models.ForeignKey(Office, on_delete=models.PROTECT) # Should not delete office if staff exists? Or CASCADE? PROTECT is safer for history.
    date_of_joining = models.DateField()
    date_of_transfer = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.pen})"

class UserAssignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignments', to_field='username')
    staff_member = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name='assignments', to_field='pen')
    from_date = models.DateField()
    to_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'from_date')

    @property
    def is_active(self):
        today = timezone.now().date()
        is_started = self.from_date <= today
        is_not_ended = self.to_date is None or self.to_date >= today
        return is_started and is_not_ended
        
    def clean(self):
        from django.core.exceptions import ValidationError
        # Check for overlapping assignments for this user
        overlapping = UserAssignment.objects.filter(
            user=self.user,
            from_date__lte=self.to_date or timezone.now().date().replace(year=2100), # effectively max date
            to_date__gte=self.from_date
        ).exclude(pk=self.pk)
        
        # Handle the case where existing assignments might have null to_date (meaning active indefinitely)
        # and we are trying to add a new one. 
        # Logic: Simple temporal overlap check.
        # Overlap if: (StartA <= EndB) and (EndA >= StartB)
        

        
        # Let's do a robust query-based check which is standard
        # We need to handle the None (infinity) correctly in the query.
        
        # Filter for assignments for this user
        qs = UserAssignment.objects.filter(user=self.user).exclude(pk=self.pk)
        
        # Overlap Condition:
        # (Existing.Start <= New.End) AND (Existing.End >= New.Start)
        # Where NULL End means Infinity.
        
        # Case 1: Existing has explicit to_date
        # Case 2: Existing has NULL to_date
        
        # This is complex to do purely in ORM without some Q object acrobatics involving IsNull.
        # Let's iterate as it's safer and volume is low per user.
        
        for existing in qs:
            existing_start = existing.from_date
            existing_end = existing.to_date # None = Infinity
            
            new_start = self.from_date
            new_end = self.to_date # None = Infinity
            
            # Check for non-overlap first
            
            # 1. Existing ends before New starts?
            if existing_end and existing_end < new_start:
                continue # No overlap
                
            # 2. Existing starts after New ends?
            if new_end and existing_start > new_end:
                continue # No overlap
            
            # If neither, they overlap
            raise ValidationError(f"Assignment overlaps with existing assignment for {self.user} assigned to {existing.staff_member} ({existing.from_date} - {existing.to_date or 'Indefinite'})")

    def __str__(self):
        return f"{self.user} -> {self.staff_member}"

class LoginSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    staff_member = models.ForeignKey(StaffMember, on_delete=models.SET_NULL, null=True, related_name='sessions')
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user} at {self.login_time}"
