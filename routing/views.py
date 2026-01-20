from django.views.generic import ListView, View, TemplateView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db import transaction
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.utils import timezone
from .models import DeskQueue, VisitLock
from datetime import timedelta
from .services import (
    attend_visit, transfer_visit, complete_visit,
    get_visit_queue, get_desk_queue, assign_visit_to_desk
)
from visit_regn.models import Visit, Purpose
from accounts.models import Desk
from visit_regn.forms import VisitRegistrationForm

class VisitQueueView(LoginRequiredMixin, ListView):
    template_name = 'routing/office_queue.html'
    context_object_name = 'queue_items'

    def get_queryset(self):
        # Shows all active queue items for the user's office
        if not self.request.user.office:
            return DeskQueue.objects.none()
        return get_visit_queue(self.request.user.office)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add user's desk to context to highlight or enable actions
        context['user_desk'] = self.request.user.desk
        context['all_purposes'] = Purpose.objects.all()
        if self.request.user.office:
            # Filter desks: Exclude current user's desk and 'Visitor' desk
            desks = Desk.objects.filter(office=self.request.user.office)
            if self.request.user.desk:
                desks = desks.exclude(id=self.request.user.desk.id)
            desks = desks.exclude(name__icontains='Visitor')
            context['all_desks'] = desks
        return context

class DeskQueueView(LoginRequiredMixin, ListView):
    template_name = 'routing/my_desk_queue.html'
    context_object_name = 'desk_items'

    def get_queryset(self):
        if not self.request.user.desk:
            return DeskQueue.objects.none()
        return get_desk_queue(self.request.user.desk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Provide all desks for the transfer dropdown
        if self.request.user.office:
             context['all_desks'] = Desk.objects.filter(office=self.request.user.office)
        else:
             context['all_desks'] = Desk.objects.none()
        context['all_purposes'] = Purpose.objects.all()
        return context

class VisitAttendView(LoginRequiredMixin, View):
    def post(self, request, visit_id):
        visit = get_object_or_404(Visit, id=visit_id)
        
        # Check if user has a desk
        if not request.user.desk:
            messages.error(request, "You do not have a desk assigned.")
            return redirect('routing:office_queue')

        # Logic: If I click "Call", and it's not at my desk, I am "Picking it up".
        # So we transfer it to my desk first.
        if request.user.desk != visit.current_desk:
            # Check if it's already being attended by someone else?
            # If status is IN_PROGRESS and desk is different, maybe warn?
            # But requirement says "token is considered to be open for assignment".
            # So we grab it.
            assign_visit_to_desk(visit, request.user.desk, by_user=request.user, remarks="picked from queue")
            # Refresh visit object to ensure current_desk is updated in memory if needed
            visit.refresh_from_db()

        # Now proceed to attend
        attend_visit(visit, request.user)
        messages.success(request, f"Attending token {visit.token}")
        return redirect('transactions:process_transaction', visit_id=visit.id)

class VisitTransferView(LoginRequiredMixin, View):
    def post(self, request, visit_id):
        visit = get_object_or_404(Visit, id=visit_id)
        target_desk_id = request.POST.get('target_desk')
        remarks = request.POST.get('remarks')
        
        target_desk = get_object_or_404(Desk, id=target_desk_id)
        
        # Verify user has permission (is at current desk? or VO?)
        can_transfer = (request.user.desk == visit.current_desk) or (request.user.role == 'VO')
        
        if not can_transfer:
             messages.error(request, "Permission denied.")
             return redirect('routing:desk_queue')

        transfer_visit(visit, visit.current_desk, target_desk, request.user, remarks)
        messages.success(request, f"Transferred token {visit.token} to {target_desk.name}")
        
        # If VO, go back to Office Queue. Others stay on Desk Queue.
        if request.user.role == 'VO':
            return redirect('routing:visit_queue')
            
        return redirect('routing:desk_queue')

class VisitCompleteView(LoginRequiredMixin, View):
    def post(self, request, visit_id):
        visit = get_object_or_404(Visit, id=visit_id)
        remarks = request.POST.get('remarks')
        
        if request.user.desk != visit.current_desk:
            messages.error(request, "You can only complete visits at your desk.")
            return redirect('routing:desk_queue')
            
        complete_visit(visit, request.user, remarks)
        messages.success(request, f"Completed token {visit.token}")
        return redirect('routing:desk_queue')

class VORoutingView(LoginRequiredMixin, ListView):
    """
    Shows visits that need manual routing or everything?
    Typically finding 'WAITING_VO' items or just generic override?
    Let's interpret 'VORoutingView - Lists tokens pending VO routing' meant non-routine ones.
    But effectively VO can see everything.
    """
    template_name = 'routing/vo_routing.html'
    context_object_name = 'visits'

    def get_queryset(self):
        # Filter visits in office that are WAITING or in VO Queue
        # Or specifically items in VO Desk Queue?
        # If 'send_to_vo_queue' assigned to VO desk, they appear in DeskQueueView if user is VO.
        # But this view might be for "General Routing Override".
        # Let's show all visits in office that are NOT completed/cancelled, to allow reassignment.
        if not self.request.user.office:
            return Visit.objects.none()
            
        # Use explicit range filter for today
        today = timezone.localdate()
        from datetime import datetime, time
        start_of_day = timezone.make_aware(datetime.combine(today, time.min))
        end_of_day = timezone.make_aware(datetime.combine(today, time.max))

        return Visit.objects.filter(
            office=self.request.user.office,
            status__in=[Visit.Status.WAITING, Visit.Status.ROUTED, Visit.Status.IN_PROGRESS],
            token_issue_time__range=(start_of_day, end_of_day)
        ).order_by('token_issue_time')


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['desks'] = Desk.objects.filter(office=self.request.user.office)
        return context

    def post(self, request):
        # Handle manual routing assignment
        visit_id = request.POST.get('visit_id')
        desk_id = request.POST.get('desk_id')
        visit = get_object_or_404(Visit, id=visit_id)
        desk = get_object_or_404(Desk, id=desk_id)
        
        assign_visit_to_desk(visit, desk, by_user=request.user, remarks="Manual routing by VO")
        messages.success(request, f"Assigned {visit.token} to {desk.name}")
        return redirect('routing:vo_routing')




class EditVisitView(LoginRequiredMixin, View):
    def post(self, request, visit_id):
        visit = get_object_or_404(Visit, id=visit_id)
        
        # 1. Update Details
        form = VisitRegistrationForm(request.POST, instance=visit)
        
        if form.is_valid():
            visit = form.save()
            # messages.success(request, f"Updated details for {visit.token}") -- Too noisy if just calling
            
            action = request.POST.get('action')

            # 2. Check for Assignment Action
            if action == 'assign':
                target_desk_id = request.POST.get('target_desk')
                remarks = request.POST.get('remarks')
                
                if target_desk_id:
                     target_desk = get_object_or_404(Desk, id=target_desk_id)
                     
                     # Permission check (VO or current desk)
                     can_transfer = (request.user.role == 'VO') or (request.user.desk == visit.current_desk)
                     
                     if can_transfer:
                         transfer_visit(visit, visit.current_desk, target_desk, request.user, remarks)
                         messages.success(request, f"Assigned {visit.token} to {target_desk.name}")
                     else:
                         messages.error(request, "Permission denied for assignment.")
                else:
                    messages.error(request, "Please select a target desk for assignment.")
            
            # 3. Handle "Call Now" (Save & Call)
            # CRITICAL: This combines saving edits and calling the token.
            # Do NOT remove this logic or separate the actions, as staff expect edits to be saved immediately upon clicking "Call".
            elif action == 'call':
                # Check if user has a desk
                if not request.user.desk:
                    messages.error(request, "You do not have a desk assigned.")
                    return redirect('routing:office_queue')

                # Logic: If I click "Call", and it's not at my desk, I am "Picking it up".
                if request.user.desk != visit.current_desk:
                    assign_visit_to_desk(visit, request.user.desk, by_user=request.user, remarks="picked from queue")
                    visit.refresh_from_db()

                # Now proceed to attend
                attend_visit(visit, request.user)
                messages.success(request, f"Attending token {visit.token}")
                return redirect('transactions:process_transaction', visit_id=visit.id)
            
            else:
                # Just a normal save
                messages.success(request, f"Updated details for {visit.token}")

        else:
            # Error handling
            error_msg = "Update Failed: "
            for field, errors in form.errors.items():
                error_msg += f"{field}: {', '.join(errors)}; "
            messages.error(request, error_msg)
            
        # Redirect back to the page they came from (Queue or Desk)
        return redirect(request.META.get('HTTP_REFERER', 'routing:desk_queue'))

class LockVisitView(LoginRequiredMixin, View):
    """
    API to lock a visit for viewing.
    Expects POST with visit_id.
    """
    def post(self, request, visit_id):
        visit = get_object_or_404(Visit, id=visit_id)
        
        # 1. Clean up expired locks first
        VisitLock.objects.filter(expires_at__lt=timezone.now()).delete()
        
        # 2. Check if already locked by SOMEONE ELSE
        existing_lock = VisitLock.objects.filter(visit=visit).first()
        if existing_lock:
            if existing_lock.locked_by != request.user:
                # Locked by someone else
                return JsonResponse({
                    'success': False, 
                    'message': f'Locked by {existing_lock.locked_by.username}',
                    'locked_by': existing_lock.locked_by.username
                })
            else:
                # Locked by me, extend it
                existing_lock.expires_at = timezone.now() + timedelta(minutes=2)
                existing_lock.save()
                return JsonResponse({'success': True, 'message': 'Lock extended'})
        
        # 3. Create new lock
        # Default lock duration: 2 minutes
        VisitLock.objects.create(
            visit=visit,
            locked_by=request.user,
            expires_at=timezone.now() + timedelta(minutes=2)
        )
        return JsonResponse({'success': True, 'message': 'Locked'})

class UnlockVisitView(LoginRequiredMixin, View):
    """
    API to unlock a visit.
    """
    def post(self, request, visit_id):
        visit = get_object_or_404(Visit, id=visit_id)
        # Release lock if held by user (or force if needed? Safer to only allow owner)
        VisitLock.objects.filter(visit=visit, locked_by=request.user).delete()
        return JsonResponse({'success': True})

class CheckLockView(LoginRequiredMixin, View):
    """
    API to check lock status of a visit.
    """
    def get(self, request, visit_id):
        # clean expired
        VisitLock.objects.filter(expires_at__lt=timezone.now()).delete()
        
        lock = VisitLock.objects.filter(visit_id=visit_id).select_related('locked_by').first()
        if lock:
             return JsonResponse({
                 'is_locked': True,
                 'locked_by': lock.locked_by.username,
                 'is_me': (lock.locked_by == request.user)
             })
        return JsonResponse({'is_locked': False})

