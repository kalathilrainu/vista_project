from django.utils import timezone
from .models import VisitLog, Visit
from accounts.models import UserAssignment

def log_visit_action(visit, action, by_user=None, remarks=None, from_desk=None, to_desk=None):
    """
    Creates a VisitLog entry.
    Tries to resolve by_staff from by_user using UserAssignment.
    """
    staff_member = None
    if by_user:
        # Try to find active assignment for this user
        # UserAssignment has to_field='username' for user? No, UserAssignment user FK is to User object. 
        # But 'to_field' was set in models.
        # UserAssignment model: user = FK(User, to_field='username').
        # So we can query easily.
        today = timezone.localdate()
        assignment = UserAssignment.objects.filter(
            user=by_user,
            from_date__lte=today
        ).filter(
            models.Q(to_date__gte=today) | models.Q(to_date__isnull=True)
        ).first()

        if assignment:
            staff_member = assignment.staff_member

    VisitLog.objects.create(
        visit=visit,
        action=action,
        by_user=by_user,
        by_staff=staff_member,
        from_desk=from_desk,
        to_desk=to_desk,
        remarks=remarks
    )

def route_visit_stub(visit):
    """
    Stub for routing.services.route_visit(visit).
    Tries to import the real routing module. If it fails, acts as a stub.
    """
    try:
        from routing import services as routing_services
        # Assuming routing_services.route_visit(visit) exists and returns something or modifies visit
        return routing_services.route_visit(visit)
    except ImportError:
        # Stub behavior: 
        # Just return ('ROUTED', desk_id) or similar, but simplified.
        # Let's verify if we should assign a desk here?
        # For simulation, we can log that routing is pending or simulated.
        
        # If we really want to simulate routing, we could assign to a random desk in the office?
        # But for now, we just pass. The prompt says: "Visit remains WAITING and VisitLog should note routing failure" if routing fails.
        # But this function is "provide a simple stub... that returns ('ROUTED', desk_id)".
        
        # Finding a candidate desk
        candidate_desk = visit.office.desks.first()
        if candidate_desk:
            visit.current_desk = candidate_desk
            visit.status = Visit.Status.ROUTED
            visit.save()
            
            log_visit_action(visit, 'ROUTED', remarks="Routed by Stub Service", to_desk=candidate_desk)
            return ('ROUTED', candidate_desk.id)
        else:
            # If no desks, stay waiting
            return ('WAITING', None)

from django.db import models # imported for Q objects inside function, need top level
