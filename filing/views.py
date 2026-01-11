from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.views.generic import ListView
from django.db.models import Q
from django.http import JsonResponse
from .models import OfficeFile, DocumentSubmission
from .forms import OfficeFileForm, DocumentSubmissionForm
from visit_regn.models import Visit
from routing.models import DeskQueue

def search_office_file(ref_number, office=None):
    """Helper to find file by File Number or Token, optionally scoped to office."""
    if not ref_number:
        return None
    ref_number = ref_number.strip()
    
    # 1. Exact File Number
    qs = OfficeFile.objects.filter(file_number__iexact=ref_number)
    if office:
        qs = qs.filter(office=office)
    f = qs.first()
        
    if f: return f
    
    # 2. Token match (Slightly harder to scope via Token as Visit doesn't always hav related file directly querable efficiently)
    # But usually office scope is safe on file_number.
    
    # Case A: The token *started* the file (OneToOne)
    visit_qs = Visit.objects.filter(token__iexact=ref_number)
    if office:
        visit_qs = visit_qs.filter(office=office)
    visit = visit_qs.first()
    
    if visit:
        if hasattr(visit, 'office_file'):
            return visit.office_file
        if visit.related_office_file:
            return visit.related_office_file
            
    return None

class CheckFileStatusView(View):
    def get(self, request):
        ref = request.GET.get('ref', '')
        # Determine office context
        office = None
        if request.user.is_authenticated and hasattr(request.user, 'office'):
            office = request.user.office
            
        office_file = search_office_file(ref, office=office)
        
        if office_file:
            return JsonResponse({
                'found': True,
                'file_number': office_file.file_number,
                'status': office_file.status,
                # Additional details for Closed files
                'closed_details': {
                    'closed_date': office_file.updated_at.strftime('%d %b %Y') if office_file.status == 'CLOSED' else None,
                    'reply_to': office_file.reply_to,
                    'remarks': office_file.remarks1 or office_file.remarks2
                }
            })
        return JsonResponse({'found': False})

class FileListView(LoginRequiredMixin, ListView):
    template_name = 'filing/file_list.html'
    context_object_name = 'files'

    def get_queryset(self):
        user = self.request.user
        
        # 1. VO (Manager) sees ALL pending files in their office
        if user.role == 'VO':
             return OfficeFile.objects.filter(
                 office=user.office
             ).exclude(status='CLOSED').order_by('-updated_at')

        # 2. Other Staff see files assigned to their desk
        if not user.desk:
            return OfficeFile.objects.none()
            
        return OfficeFile.objects.filter(
            desk=user.desk
        ).exclude(status='CLOSED').order_by('-updated_at')


class FileCreateView(LoginRequiredMixin, View):
    template_name = 'filing/file_create.html'

    # GET request now handles creation automatically
    def get(self, request, visit_id):
        visit = get_object_or_404(Visit, pk=visit_id)
        
        # Check if file already exists (Legacy OneToOne)
        if hasattr(visit, 'office_file'):
            messages.info(request, "File already exists for this visit.")
            return redirect('filing:file_detail', file_id=visit.office_file.id)
            
        # Check if already linked via Foreign Key
        if visit.related_office_file:
             messages.info(request, f"Visit linked to File {visit.related_office_file.file_number}")
             return redirect('filing:file_detail', file_id=visit.related_office_file.id)

        # Smart Lookup via Reference Number
        if visit.reference_number:
            linked_file = search_office_file(visit.reference_number)
            if linked_file:
                # MATCH FOUND
                
                # Check Status
                if linked_file.status == 'CLOSED':
                    # Allow user to decide what to do, but show warning page first
                    return render(request, 'filing/file_closed_info.html', {'office_file': linked_file, 'visit': visit})
                else:
                    # OPEN -> Auto Link
                    visit.related_office_file = linked_file
                    visit.save()
                    messages.success(request, f"Automatically linked to existing File {linked_file.file_number}")
                    return redirect('filing:file_detail', file_id=linked_file.id)

        # Auto-create new file immediately
        office_file = OfficeFile(
            visit=visit,
            desk=request.user.desk,
            status='OPEN' # Default
        )
        office_file.save()
        messages.success(request, f"File {office_file.file_number} created automatically.")
        return redirect('filing:file_detail', file_id=office_file.id)

    # Post method removed as form is no longer used for creation


class FileDetailView(LoginRequiredMixin, View):
    template_name = 'filing/file_detail.html'

    def get(self, request, file_id):
        office_file = get_object_or_404(OfficeFile, pk=file_id)
        file_form = OfficeFileForm(instance=office_file)
        doc_form = DocumentSubmissionForm()
        
        return render(request, self.template_name, {
            'office_file': office_file,
            'file_form': file_form,
            'doc_form': doc_form
        })

    def post(self, request, file_id):
        office_file = get_object_or_404(OfficeFile, pk=file_id)
        
        if 'update_file' in request.POST:
            file_form = OfficeFileForm(request.POST, instance=office_file)
            if file_form.is_valid():
                file_form.save()
                messages.success(request, "File details updated.")
                
                if request.POST.get('action') == 'close':
                    return redirect('dashboard')
                    
                return redirect('filing:file_detail', file_id=file_id)
                
        elif 'add_document' in request.POST:
            doc_form = DocumentSubmissionForm(request.POST)
            if doc_form.is_valid():
                doc = doc_form.save(commit=False)
                doc.office_file = office_file
                doc.submitted_by = request.user
                doc.save()
                messages.success(request, "Document added.")
                return redirect('filing:file_detail', file_id=file_id)

        # Fallback if invalid
        file_form = OfficeFileForm(instance=office_file)
        doc_form = DocumentSubmissionForm()
        return render(request, self.template_name, {
            'office_file': office_file,
            'file_form': file_form,
            'doc_form': doc_form
        })
