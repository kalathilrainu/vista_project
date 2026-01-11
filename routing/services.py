from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from visit_regn.models import Visit, VisitLog
from visit_regn.services import log_visit_action
from accounts.models import UserAssignment, Desk, User
from .models import DeskQueue, RoutingRule

def route_visit(visit):
    """
    Main entry point for routing a visit.
    Attempts auto-routing. If fails, sends to VO queue.
    """
    # 1. Try auto-routing
    try:
        routed_desk = auto_route_visit(visit)
        if routed_desk:
            return ('ROUTED', routed_desk.id)
    except Exception as e:
        # Log the failure but don't crash
        log_visit_action(visit, VisitLog.Action.COMMENT, remarks=f"Auto-routing failed: {str(e)}")

    # 2. Fallback: Send to VO Queue
    # We need to find the VO desk for this office.
    # Assuming 'Village Officer' role or specific desk name?
    # Better: Use RoutingRule with Purpose=None ?? No.
    # Requirement: "If purpose has default desk -> Assign... Non-routine -> routed by VO"
    # "Non-routine -> routed by VO" means we should send to VO desk.
    
    send_to_vo_queue(visit)
    return ('WAITING_VO', None) # Indicates waiting for VO

def auto_route_visit(visit):
    """
    Determines if purpose has a default desk and assigns it.
    Returns Desk object if routed, None otherwise.
    """
    office = visit.office
    purpose = visit.purpose
    
    # Find rule
    rule = RoutingRule.objects.filter(office=office, purpose=purpose).first()
    
    if rule:
        assign_visit_to_desk(visit, rule.default_desk, by_user=None, remarks="Auto-routed based on purpose")
        return rule.default_desk
    
    return None

def send_to_vo_queue(visit):
    """
    Assigns to VO desk.
    """
    office = visit.office
    
    # Strategy to find VO desk:
    # 1. Look for a desk named 'Village Officer' or 'VO'
    # 2. Or check if there is a VO user and get their desk?
    # Let's try to find a desk with user having role 'VO'
    
    vo_desk = None
    
    # Try finding desk by name first (convention)
    # Priority 1: Exact Request for 'Village Officer'
    vo_desk = Desk.objects.filter(office=office, name__iexact='Village Officer').first()
    
    # Priority 2: Exact 'VO'
    if not vo_desk:
        vo_desk = Desk.objects.filter(office=office, name__iexact='VO').first()

    # Priority 3: Starts with 'VO' (e.g. "VO Desk")
    if not vo_desk:
        vo_desk = Desk.objects.filter(office=office, name__istartswith='VO').first()
        
    # Priority 3: Contains 'Village Officer' (safer than just 'VO' which matches SVO)
    if not vo_desk:
        vo_desk = Desk.objects.filter(office=office, name__icontains='Village Officer').first()
    
    if not vo_desk:
        # Fallback: Find any desk? No, that's dangerous.
        # Log failure
        log_visit_action(visit, VisitLog.Action.COMMENT, remarks="Could not find VO Desk to route non-routine visit.")
        return False

    assign_visit_to_desk(visit, vo_desk, by_user=None, remarks="Sent to VO Queue for manual routing")
    return True

@transaction.atomic
def assign_visit_to_desk(visit, desk, by_user=None, remarks=None):
    """
    Assigns visit to a desk.
    Updates Visit, creates DeskQueue, logs action.
    """
    old_desk = visit.current_desk
    
    # 1. Update Visit
    visit.current_desk = desk
    if visit.status == Visit.Status.WAITING:
        visit.status = Visit.Status.ROUTED # Only change status if it was waiting. If IN_PROGRESS, might be transfer?
    elif visit.status == Visit.Status.IN_PROGRESS:
        # If transferring, it goes back to ROUTED state (waiting at new desk)?
        # Usually yes.
        visit.status = Visit.Status.ROUTED
        visit.token_attend_time = None # Reset attend time? Maybe. Let's keep it simple.
    
    visit.save()
    
    # 2. Manage DeskQueue
    # Remove from old queue if exists
    DeskQueue.objects.filter(visit=visit).delete() # Simple overwrite
    
    # Create new queue entry
    DeskQueue.objects.create(
        visit=visit,
        desk=desk,
        assigned_by=by_user,
        is_active=True
    )
    
    # 3. Log
    action = VisitLog.Action.ASSIGNED
    # If it's a transfer (old_desk exists), we might log TRANSFERRED instead?
    # This function is generic assignment. Let's stick to ASSIGNED or let caller specify logic?
    # Requirement says "Log ASSIGNED".
    # But `transfer_visit` calls this?
    
    if not remarks:
        remarks = f"Assigned to {desk.name}"
        
    log_visit_action(visit, action, by_user=by_user, from_desk=old_desk, to_desk=desk, remarks=remarks)

@transaction.atomic
def attend_visit(visit, by_user):
    """
    Staff attends a visit.
    """
    # Verify user belongs to the desk? View layer should check.
    # Here we just execute.
    
    visit.status = Visit.Status.IN_PROGRESS
    visit.token_attend_time = timezone.now()
    visit.save()
    
    log_visit_action(visit, VisitLog.Action.ATTENDED, by_user=by_user)
    
@transaction.atomic
def transfer_visit(visit, from_desk, to_desk, by_user, remarks):
    """
    Transfer visit from one desk to another.
    """
    # Re-use assignment logic
    assign_visit_to_desk(visit, to_desk, by_user=by_user, remarks=remarks)
    
    # We want to log TRANSFERRED, but assign_visit_to_desk logs ASSIGNED.
    # Maybe we should explicitly log TRANSFERRED here?
    # The requirement says: "Log TRANSFERRED with remarks".
    # `assign_visit_to_desk` logs ASSIGNED.
    # Let's add an explicit log entry for TRANSFERRED or modify `assign_visit_to_desk` to take action type?
    # Let's just log TRANSFERRED additionally to be safe and explicit.
    log_visit_action(visit, VisitLog.Action.TRANSFERRED, by_user=by_user, from_desk=from_desk, to_desk=to_desk, remarks=remarks)

@transaction.atomic
def complete_visit(visit, by_user, remarks):
    """
    Mark visit as completed.
    """
    visit.status = Visit.Status.COMPLETED
    visit.save()
    
    # Remove from active queue
    DeskQueue.objects.filter(visit=visit).update(is_active=False)
    
    log_visit_action(visit, VisitLog.Action.COMPLETED, by_user=by_user, remarks=remarks)

from datetime import timedelta
from django.db.models import Q

def get_visit_queue(office):
    """
    Returns all active DeskQueue items for the office.
    Ordered by assigned_at (FIFO).
    """
    # Fix: Use date range instead of __date lookup to avoid timezone issues/misunderstandings
    today = timezone.localdate()
    
    # Create timezone-aware start and end of day
    # Note: timezone.now() is aware if USE_TZ=True. 
    # timezone.make_aware requires a naive datetime if converting.
    # datetime.combine returns naive.
    from datetime import datetime, time
    start_of_day = timezone.make_aware(datetime.combine(today, time.min))
    end_of_day = timezone.make_aware(datetime.combine(today, time.max))

    # Inclusive Desk Filtering
    q_desk = Q(desk__name__istartswith='VO') | \
             Q(desk__name__icontains='Village Officer') | \
             Q(desk__name__iexact='VISITOR') | \
             Q(desk__name__iexact='Visitor')

    return DeskQueue.objects.filter(visit__office=office, is_active=True)\
        .filter(visit__token_issue_time__range=(start_of_day, end_of_day))\
        .filter(q_desk)\
        .exclude(visit__status=Visit.Status.IN_PROGRESS)\
        .select_related('visit', 'desk', 'visit__purpose', 'visit__active_lock')\
        .order_by('visit__token')


def get_desk_queue(desk):
    """
    Returns active items for a specific desk.
    """
    office = desk.office
    
    # Date Range Filter
    today = timezone.localdate()
    from datetime import datetime, time
    start_of_day = timezone.make_aware(datetime.combine(today, time.min))
    end_of_day = timezone.make_aware(datetime.combine(today, time.max))

    # Base Query
    queryset = DeskQueue.objects.filter(desk=desk, is_active=True)\
        .filter(visit__token_issue_time__range=(start_of_day, end_of_day))\
        .select_related('visit', 'visit__purpose')

    # SPECIAL LOGIC: 
    # If this desk is a "General Queue" desk (VO/Visitor), 
    # we do NOT want to show items that were just system-dumped here (assigned_by=None) 
    # unless they are already being worked on (IN_PROGRESS).
    
    # Check if this desk is a "General Desk" using permissive check
    is_general_desk = False
    name_lower = desk.name.lower()
    if name_lower.startswith('vo') or 'village officer' in name_lower or name_lower == 'visitor':
        is_general_desk = True

    if is_general_desk:
        # Exclude if: (Assigned by None AND Status is NOT In Progress)
        queryset = queryset.exclude(
             assigned_by__isnull=True, 
             visit__status__in=['WAITING', 'ROUTED']
        )
    
    return queryset

