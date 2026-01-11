from django import template
from accounts.utils import get_current_staff_for_user

register = template.Library()

@register.filter
def get_current_staff_name(user):
    """
    Returns the name of the currently assigned StaffMember for the given User,
    or None if no assignment is active.
    """
    staff = get_current_staff_for_user(user)
    if staff:
        return staff.name
    return None
