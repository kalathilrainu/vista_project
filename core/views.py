from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
# Import specific models if they exist, otherwise use placeholders or try-except
try:
    # from visits.models import Token  # Legacy module removed
    from applications.models import Application
    from tapal.models import Tapal
except ImportError:
    pass

def landing(request):
    """
    Public Home Page
    """
    context = {
        'announcements': [
            'Village Office working hours: 10 AM - 5 PM',
            'Land Tax payment due date extended',
            'Pension mustering camp on Saturday'
        ]
    }

    # Generate Simple Math CAPTCHA
    import random
    
    num1 = random.randint(1, 9)
    num2 = random.randint(1, 9)
    # Using addition only for simplicity and mobile-friendliness
    question = f"What is {num1} + {num2}?"
    answer = num1 + num2
    
    request.session['captcha_expected'] = answer
    context['captcha_question'] = question

    return render(request, 'home.html', context)

@login_required
def dashboard(request):
    """
    Staff Dashboard
    """
    # Redirect Admins to User Management Dashboard
    if request.user.is_superuser or request.user.role in ['ADMIN', 'SUPER_ADMIN']:
        return redirect('user_management')

    # Placeholder logic for KPIs since models might be empty or in flux
    # In production, these would be real queries:
    # visits_today = Visit.objects.filter(date=today).count()
    
    from routing.services import get_visit_queue, get_desk_queue
    from filing.models import OfficeFile
    from visit_regn.models import Visit

    # Calculate real KPIs
    # get_visit_queue expects 'office' object
    visit_queue_count = 0
    if request.user.office:
        visit_queue_count = get_visit_queue(request.user.office).count()

    # get_desk_queue expects 'desk' object
    my_desk_queue_count = 0
    if request.user.desk:
        my_desk_queue_count = get_desk_queue(request.user.desk).count()
    
    # Office Files Logic (Same as FileListView)
    if request.user.role == 'VO':
         office_files_count = OfficeFile.objects.filter(
             office=request.user.office
         ).exclude(status='CLOSED').count()
    elif request.user.desk:
        office_files_count = OfficeFile.objects.filter(
            desk=request.user.desk
        ).exclude(status='CLOSED').count()
    else:
        office_files_count = 0

    kpis = {
        'visit_queue': visit_queue_count,
        'my_desk': my_desk_queue_count,
        'office_files': office_files_count,
        # 'tokens': 5  # Legacy placeholder
    }

    recent_activity = [
        # Placeholder activity for now, can be real later
        {'time': timezone.now().strftime('%I:%M %p'), 'description': 'System Dashboard Loaded'},
    ]

    context = {
        'kpis': kpis,
        'recent_activity': recent_activity
    }
    return render(request, 'dashboard_home.html', context)



def track_status(request):
    """
    Public View to Track Visit Token or File Status
    """
    query = request.GET.get('q', '').strip()
    result = None
    
    # Import locally to avoid circular imports if any
    from visit_regn.models import Visit
    from filing.models import OfficeFile

    if query:
        # 1. Try Searching for Visit by Token
        try:
            visit = Visit.objects.get(token__iexact=query)
            result = {
                'type': 'Visit Token',
                'ref': visit.token,
                'status': visit.get_status_display(),
                'date': visit.token_issue_time,
                'location': visit.current_desk.name if visit.current_desk else "Waiting Area",
                'office': visit.office.name if visit.office else "General",
                'obj': visit 
            }
            # ... (same linked logic) ...
            linked_file = None
            if hasattr(visit, 'office_file'):
                linked_file = visit.office_file
            elif visit.related_office_file:
                 linked_file = visit.related_office_file
            
            if linked_file:
                result['linked_type'] = 'Office File'
                result['linked_ref'] = linked_file.file_number
                result['linked_status'] = linked_file.get_status_display()
                if linked_file.interim_status:
                     result['linked_status'] += f" ({linked_file.interim_status})"
                result['linked_location'] = linked_file.desk.name if linked_file.desk else "Record Room/Pending"

        except Visit.DoesNotExist:
            # 2. Try Searching for Office File by File Number (Handle Duplicates)
            matching_files = OfficeFile.objects.filter(file_number__iexact=query)
            
            if matching_files.exists():
                count = matching_files.count()
                if count == 1:
                    office_file = matching_files.first()
                    result = {
                        'type': 'Office File',
                        'ref': office_file.file_number,
                        'status': office_file.get_status_display(),
                        'date': office_file.created_at,
                        'location': office_file.desk.name if office_file.desk else "Record Room/Pending",
                        'office': office_file.office.name if office_file.office else "General", # Show Office Name
                        'obj': office_file
                    }
                    if office_file.interim_status and office_file.interim_status != office_file.get_status_display():
                         result['status'] += f" ({office_file.interim_status})"

                    if office_file.visit:
                        result['linked_type'] = 'Original Visit Token'
                        result['linked_ref'] = office_file.visit.token
                        result['linked_status'] = office_file.visit.get_status_display()
                        result['linked_location'] = office_file.visit.current_desk.name if office_file.visit.current_desk else "Completed"
                else:
                    # Multiple matches found
                    result = {
                        'type': 'Multiple Matches',
                        'count': count,
                        'matches': []
                    }
                    for f in matching_files:
                        match_data = {
                            'ref': f.file_number,
                            'office': f.office.name if f.office else "Unknown Office",
                            'status': f.get_status_display(),
                            'date': f.created_at,
                            'id': f.id # To potentially link to a detail view if URL structure allowed, but query is safe enough
                        }
                        result['matches'].append(match_data)

    
    context = {
        'query': query,
        'result': result
    }
    return render(request, 'track_status.html', context)
