from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from .models import Transaction
from .forms import TransactionForm
from visit_regn.models import Visit
from visit_regn.forms import VisitStaffUpdateForm
from routing.models import DeskQueue

class TransactionCreateView(LoginRequiredMixin, View):
    template_name = 'transactions/transaction_process.html'

    def get(self, request, visit_id):
        visit = get_object_or_404(Visit, pk=visit_id)
        # Check if transaction exists, if so resume it, otherwise create
        transaction, created = Transaction.objects.get_or_create(visit=visit)
        
        # If transaction is already closed, maybe redirect or show read-only? 
        # For now assume we are editing active.
        
        form = TransactionForm(instance=transaction)
        visit_form = VisitStaffUpdateForm(instance=visit)
        
        visit_form = VisitStaffUpdateForm(instance=visit)
        
        source = request.GET.get('source', '')
        
        # Smart File Detection Logic
        detected_files = []
        found_file_ids = set()
        
        from filing.models import OfficeFile
        from django.db.models import Q
        
        # Step A: Reference Number Search
        if visit.reference_number:
            ref = visit.reference_number.strip()
            # Search for OPEN files by File Number OR Valid Token
            ref_matches = OfficeFile.objects.filter(
                Q(file_number__iexact=ref) | 
                Q(visit__token__iexact=ref),
                status='OPEN'
            )
            
            for file in ref_matches:
                if file.id in found_file_ids:
                    continue
                    
                alert_type = 'mismatch' # Default to mismatch
                
                # Check Mobile Match (Data Integrity)
                file_mobile = file.visit.mobile if file.visit else None
                current_mobile = visit.mobile
                
                if file_mobile and current_mobile and file_mobile == current_mobile:
                    alert_type = 'match' # Green: Verified Match
                
                detected_files.append({
                    'file': file,
                    'alert_type': alert_type
                })
                found_file_ids.add(file.id)
        
        # Step B: Mobile Number Search (Discovery - Search for ANY open files with this mobile)
        if visit.mobile:
            mobile_matches = OfficeFile.objects.filter(
                visit__mobile=visit.mobile,
                status='OPEN'
            ).order_by('-created_at')
            
            for file in mobile_matches:
                if file.id in found_file_ids:
                    continue
                
                # If found here, it wasn't a direct ref match, so it's a discovery
                detected_files.append({
                    'file': file,
                    'alert_type': 'mobile_discovery'
                })
                found_file_ids.add(file.id)
        
        return render(request, self.template_name, {
            'form': form, 
            'visit_form': visit_form,
            'visit': visit, 
            'transaction': transaction,
            'source': source,
            'detected_files': detected_files,
        })

    def post(self, request, visit_id):
        visit = get_object_or_404(Visit, pk=visit_id)
        transaction = get_object_or_404(Transaction, visit=visit)
        
        form = TransactionForm(request.POST, instance=transaction)
        visit_form = VisitStaffUpdateForm(request.POST, instance=visit)
        
        # Validate both
        if form.is_valid() and visit_form.is_valid():
            transaction = form.save(commit=False)
            visit_form.save()
            
            action = request.POST.get('action')
            
            if action == 'close':
                transaction.status = 'CLOSED'
                visit.status = 'COMPLETED'
                visit.completed_at = timezone.now()
                visit.save()
                DeskQueue.objects.filter(visit=visit).delete()
                transaction.save()
                return redirect('dashboard') 
                
            elif action == 'open_file':
                target_file_id = request.POST.get('target_file_id')
                
                transaction.status = 'OPEN_FILE'
                visit.status = 'COMPLETED'
                visit.completed_at = timezone.now()
                visit.save()
                DeskQueue.objects.filter(visit=visit).delete()
                transaction.save()
                
                if target_file_id:
                     return redirect('filing:file_detail', file_id=target_file_id)
                else:
                     return redirect('filing:file_create', visit_id=visit.id)
            
            # Save button (no close)
            # Make sure to save transaction explicitly
            transaction.save()
            # Redirect to same page to show updated data or queue? 
            # User workflow: view -> call -> edit -> save -> maybe stay or go?
            # Usually "Check/Update" implies just saving and staying or finishing.
            # I'll redirect to queue to match previous implementation logic which was "Save -> Queue".
            # User requested redirect to Dashboard on "Complete" or "Open File".
            # For "Save", they didn't explicitly say, but "finished work... returns to queue" implies closing actions.
            # "Check/Update" is NOT finishing work, it is intermittent. 
            # If I redirect "Save" to dashboard, they leave the page. 
            # If I stay, they can continue. 
            # However, previous behavior was "Save -> Queue".
            # I will change "Save" to "Dashboard" as well if the intention is "I'm done with this edit".
            # But "Check/Update" usually implies "I want to save and keep working" or "I want to save and go back".
            # Given the request specific text: "When I have finished... and either 'Complete Visit' or 'Open File' user is getting returned to... It is better if returned to Dashboard."
            # They specifically mentioned 'Complete Visit' or 'Open File'. 
            # They did NOT mention 'Save'.
            # So I will keep 'Save' pointing to 'routing:visit_queue' OR 'dashboard'? 
            # Actually, standard behavior for "Save & Close" is dashboard. 
            # If "Save" is just "Save", it should probably reload the page. 
            # BUT, the previous code redirected to 'visit_queue'. 
            # To be safe and consistent with the "return to dashboard" request for exit actions, I will change the exit actions.
            # I will leave "Save" as is or change it to dashboard? 
            # "Check/Update" button... if I click it, I probably want to go back to my work list.
            # I will set ALL redirects to 'dashboard' to be consistent, assuming 'Save' is also an exit from this specific screen. 
            # Wait, if 'Save' exits, then how do I 'Save and Continue'? 
            # I don't have a 'Save and Continue'. I have 'Check/Update'.
            # I'll stick to 'dashboard' for the requested ones and 'visit_queue' (or 'dashboard'?) for Save.
            # Let's read the prompt again: "When I have finished the work... and either 'Complete Visit' or 'Open File'..."
            # It excludes 'Save'.
            # ill change only complete and open file.
            # Save button (no close) - Stay on page
            redirect_url = f"{reverse('transactions:process_transaction', args=[visit.id])}"
            source = request.POST.get('source')
            if source:
                redirect_url += f"?source={source}"
            return HttpResponseRedirect(redirect_url)
            
        return render(request, self.template_name, {
            'form': form, 
            'visit_form': visit_form,
            'visit': visit, 
            'transaction': transaction
        })

class VisitorDisplayView(View):
    template_name = 'transactions/visitor_display.html'
    def get(self, request):
        return render(request, self.template_name)

class GetLatestCallsView(View):
    def get(self, request):
        # Get active calls (DeskQueue items sorted by assigned_at desc)
        # Limit to 5
        calls = DeskQueue.objects.select_related('visit', 'desk').order_by('-assigned_at')[:5]
        data = []
        for call in calls:
            data.append({
                'token': call.visit.token,
                'desk': call.desk.name,
                'status': 'Calling'
            })
        return JsonResponse({'calls': data})
