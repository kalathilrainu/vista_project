from django import template
from django.utils import timezone
from accounts.models import UserAssignment

register = template.Library()

@register.simple_tag
def get_active_staff_name(user):
    """
    Returns the name of the currently assigned StaffMember for the given User.
    """
    if not user.is_authenticated:
        return ""
        
    today = timezone.now().date()
    assignment = UserAssignment.objects.filter(
        user=user,
        from_date__lte=today
    ).filter(
        to_date__isnull=True
    ).order_by('-from_date').first()
    
    if not assignment:
        # Try to find one that ends in future if infinity check failed (though isnull cover logic)
        # Re-implementing logic from utils slightly differently to be sure
        from django.db.models import Q
        assignment = UserAssignment.objects.filter(
            user=user,
            from_date__lte=today
        ).filter(
            Q(to_date__isnull=True) | Q(to_date__gte=today)
        ).order_by('-from_date').first()

    if assignment:
        return assignment.staff_member.name
    return ""
