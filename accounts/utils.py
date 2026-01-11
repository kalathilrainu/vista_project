from django.db import models
from django.utils import timezone
from .models import UserAssignment

def get_current_staff_for_user(user):
    """
    Returns the currently assigned StaffMember for the given User,
    based on the current date falling within from_date and to_date.
    """
    today = timezone.now().date()
    # Find assignment where from_date <= today AND (to_date is NULL OR to_date >= today)
    assignment = UserAssignment.objects.filter(
        user=user,
        from_date__lte=today
    ).filter(
        models.Q(to_date__isnull=True) | models.Q(to_date__gte=today)
    ).order_by('-from_date').first()
    
    if assignment:
        return assignment.staff_member
    return None

def generate_username(role, office_code):
    """
    Generates a username based on the pattern: ROLE + OFFICE_CODE + [SERIAL]
    Example: SVO + 050317 + (empty/1/2/...)
    """
    # Ensure uppercase
    role = role.upper()
    office_code = office_code.upper()
    
    base = f"{role}{office_code}"
    
    # Check if the base username exists
    # If it's a VO, they are a single post, so we might want to just return base 
    # but the logic says "First username ... will be Designation+Code", "all other ... next username ... added with serial number"
    # So even for VO, if VO050317 exists, logic implies next would be VO0503171?
    # User said: "Village Officer is single post no additional Post will be there." 
    # But let's support serial just in case or strictly check first.
    # We will stick to the generic "find first available" logic which covers both cases safely.
    
    from .models import User
    
    # Try base first
    if not User.objects.filter(username=base).exists():
        return base
    
    # Try serials starting from 1
    counter = 1
    while True:
        candidate = f"{base}{counter}"
        if not User.objects.filter(username=candidate).exists():
            return candidate
        counter += 1
