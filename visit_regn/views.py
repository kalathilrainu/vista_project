from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, CreateView, DetailView, ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.contrib import messages
from django.utils.translation import gettext as _
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Visit, VisitLog, DailyTokenCounter, Purpose
from .forms import VisitRegistrationForm, VisitActionForm
from .services import log_visit_action
from accounts.models import User, Office, Desk
from .utils import generate_token_image
import qrcode
import io
import base64
from django.http import HttpResponse, FileResponse

# Helper to get the default VISITOR user
def get_visitor_user():
    user, created = User.objects.get_or_create(username='VISITOR', defaults={'role': 'VO'}) # Role optional/dummy
    if created:
        user.set_unusable_password()
        user.save()
    return user

# Helper to get current office (Simplified: hardcoded or from request/session)
# For Kiosk, usually the device is bound to an office. 
# We'll assume a default office (e.g. first one) or from URL query param for now, 
# or set via a middleware. For MVP, I will pick the first Office or specific code '050317'.
def get_current_office(request):
    # 1. Staff Login Priority
    if request.user.is_authenticated and hasattr(request.user, 'office') and request.user.office:
        return request.user.office

    # 2. Check if user is a specific Kiosk Login (e.g. VS050317)
    if request.user.is_authenticated and request.user.username.startswith('VS') and len(request.user.username) > 2:
        code = request.user.username[2:]
        office = Office.objects.filter(code=code).first()
        if office:
            return office

    # Fallback: Try query param
    office_code = request.GET.get('office')
    if office_code:
        return get_object_or_404(Office, code=office_code)
    
    # Fallback to first office
    office = Office.objects.first()
    return office

# --- KIOSK VIEWS ---

class KioskBaseMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['office'] = get_current_office(self.request)
        return context

class KioskHomeView(KioskBaseMixin, TemplateView):
    template_name = 'visit_regn/kiosk_home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        office = context.get('office')
        
        if office:
            # Generate QR Code for Mobile Entry
            # URL: /visit/mobile-entry/?office=<code>
            # We need absolute URL for the QR code to work on mobile
            path = reverse('visit_regn:mobile_entry')
            # Assuming request.build_absolute_uri handles domain/ip
            url = self.request.build_absolute_uri(f"{path}?office={office.code}")
            
            # Generate QR
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to Base64 to embed in template
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            context['qr_code_image'] = img_str
            context['qr_url'] = url # For debugging/fallback
            
        return context

class BaseRegisterView(KioskBaseMixin, CreateView):
    model = Visit
    form_class = VisitRegistrationForm
    template_name = 'visit_regn/register_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['mode'] = self.kwargs.get('mode', 'MANUAL')
        
        # Smart Back URL
        if self.request.user.is_authenticated and not self.request.user.username.startswith('VS'):
            # Regular staff (not Kiosk user) -> Dashboard
            context['back_url'] = '/dashboard/'
        else:
            # Kiosk user or anonymous -> Kiosk Home
            context['back_url'] = reverse('visit_regn:kiosk_home')
            
        return context

    def form_valid(self, form):
        office = get_current_office(self.request)
        if not office:
            messages.error(self.request, "No Office Configured")
            return redirect('visit_regn:kiosk_home')
            
        visitor_user = get_visitor_user()
        
        # Use create_from_kiosk method
        mode = self.kwargs.get('mode', 'MANUAL')
        # We need to manually construct the data dict or use form cleaned_data
        # create_from_kiosk expects a dict-like object
        
        # But wait, create_from_kiosk is classmethod that does saving.
        # So we shouldn't use super().form_valid(form) which saves normally.
        
        visit = Visit.create_from_kiosk(
            data=form.cleaned_data, 
            office=office, 
            user=visitor_user, 
            mode=mode
        )
        
        self.object = visit
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('visit_regn:token_print', kwargs={'pk': self.object.pk})

class ManualRegisterView(BaseRegisterView):
    def get_initial(self):
        return {'mode': 'KIOSK'}
        
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs

class QrRegisterView(BaseRegisterView):
     # Same as Manual but with different mode/template context
     def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['qr_scan_mode'] = True # context flag to show different UI instruction
        return context
        
     def form_valid(self, form):
        self.kwargs['mode'] = 'QR' # Override mode
        return super().form_valid(form)

class QuickRegisterView(KioskBaseMixin, View):
    def post(self, request, *args, **kwargs):
        office = get_current_office(request)
        if not office:
            return redirect('visit_regn:kiosk_home')
            
        visitor_user = get_visitor_user()
        
        # Quick registration implies minimal data.
        # Try to find a generic purpose like "General Enquiry" or just "Enquiry"
        # Since the user complained about "Land Tax" being default, we must avoid random picking.
        
        purpose = Purpose.objects.filter(name__icontains='Enquiry').first()
        if not purpose:
             purpose = Purpose.objects.filter(name__icontains='General').first()
             
        if not purpose:
            # Create a safe default
            purpose, _ = Purpose.objects.get_or_create(name='General Enquiry')
            
        data = {
            'name': 'Guest',
            'mobile': '', # Quick reg might not have mobile? But we just made it mandatory!
            # Wait, if we made mobile mandatory in FORM, does QuickReg use the form?
            # QuickReg uses Visit.create_from_kiosk(data=...) which might bypass form validation 
            # if we construct data manually here.
            # However, if 'mobile' is blank here, and model allows generic guests..
            # Model definition: mobile = models.CharField(max_length=15, null=True, blank=True)
            # So DB accepts it. The Mandatory check was ONLY in the Form.
            # Quick Reg (one click) usually doesn't ask for mobile. So passing '' is fine for DB.
            'purpose': purpose,
            'reference_number': ''
        }
        
        visit = Visit.create_from_kiosk(
            data=data,
            office=office,
            user=visitor_user,
            mode='QUICK'
        )
        
        return redirect('visit_regn:token_print', pk=visit.pk)

    def get(self, request, *args, **kwargs):
        # Allow GET for testing/demo per prompt "single-click endpoint" but properly should be POST
        # If accessing via link button
        return self.post(request, *args, **kwargs)

class TokenPrintView(KioskBaseMixin, DetailView):
    model = Visit
    template_name = 'visit_regn/token_print.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Smart Exit URL
        if self.request.user.is_authenticated and not self.request.user.username.startswith('VS'):
            # Regular staff -> Dashboard
            context['exit_url'] = '/dashboard/'
        else:
            # Kiosk user or anonymous -> Kiosk Home
            context['exit_url'] = reverse('visit_regn:kiosk_home')
        return context


# --- MOBILE VIEWS ---

class MobileEntryView(TemplateView):
    template_name = 'visit_regn/mobile_entry.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        office_code = self.request.GET.get('office')
        if office_code:
            context['office'] = Office.objects.filter(code=office_code).first()
        
        # Pass all purposes for dropdown
        context['purposes'] = Purpose.objects.all().order_by('name')
        return context
        
    def post(self, request, *args, **kwargs):
        office_code = request.GET.get('office')
        office = Office.objects.filter(code=office_code).first()
        
        if not office:
            messages.error(request, "Invalid Office Link")
            return redirect('visit_regn:mobile_entry')
            
        # Get data from POST
        name = request.POST.get('name')
        mobile = request.POST.get('mobile')
        purpose_id = request.POST.get('purpose')
        
        visitor_user = get_visitor_user()
        
        # Purpose handling
        if purpose_id:
            purpose = Purpose.objects.filter(id=purpose_id).first()
        else:
             purpose, _ = Purpose.objects.get_or_create(name='General Enquiry')
             
        data = {
            'name': name,
            'mobile': mobile,
            'purpose': purpose,
            'reference_number': ''
        }
        
        visit = Visit.create_from_kiosk(
            data=data,
            office=office,
            user=visitor_user,
            mode='MOBILE'
        )
        
        return redirect('visit_regn:mobile_token', pk=visit.pk)

class MobileTokenView(DetailView):
    model = Visit
    template_name = 'visit_regn/mobile_token_success.html'
    context_object_name = 'visit'

class DownloadTokenView(View):
    def get(self, request, pk):
        visit = get_object_or_404(Visit, pk=pk)
        buffer = generate_token_image(visit)
        return FileResponse(buffer, as_attachment=True, filename=f"Token_{visit.token}.jpg")


# --- STAFF VIEWS ---

class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        # Check if user is staff (User.office is set or has logic)
        return self.request.user.is_authenticated and (self.request.user.office is not None or self.request.user.is_superuser)

class VisitQueueView(StaffRequiredMixin, ListView):
    model = Visit
    template_name = 'visit_regn/staff/visit_queue.html'
    context_object_name = 'visits'
    paginate_by = 20
    
    def get_queryset(self):
        # Filter by staff's office
        qs = Visit.objects.filter(
            office=self.request.user.office
        ).exclude(status__in=[Visit.Status.COMPLETED, Visit.Status.CANCELLED])
        
        # Filter by status if needed
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
            
        # If staff has a desk, maybe show routed to them?
        # But usually queue shows WAITING + ROUTED to my desk
        if self.request.user.desk:
             qs = qs.filter(
                Q(status=Visit.Status.WAITING) | 
                Q(current_desk=self.request.user.desk)
             )
        
        return qs.order_by('-token_issue_time')

class VisitDetailView(StaffRequiredMixin, DetailView):
    model = Visit
    template_name = 'visit_regn/staff/visit_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass desks for transfer/routing
        if self.request.user.office:
            desks = self.request.user.office.desks.all()
        else:
            desks = Desk.objects.none()
            
        context['action_form'] = VisitActionForm(desks=desks)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        office = request.user.office
        desks = office.desks.all() if office else Desk.objects.none()
        
        form = VisitActionForm(request.POST, desks=desks)
        
        if form.is_valid():
            action = form.cleaned_data['action']
            remarks = form.cleaned_data['remarks']
            target_desk = form.cleaned_data['target_desk']
            
            # Logic
            if action == 'ATTENDED':
                self.object.status = Visit.Status.IN_PROGRESS
                self.object.token_attend_time = timezone.now()
                self.object.current_desk = request.user.desk # Attend at my desk
                self.object.save()
                log_visit_action(self.object, 'ATTENDED', by_user=request.user, remarks=remarks)
                
            elif action == 'COMPLETED':
                self.object.status = Visit.Status.COMPLETED
                self.object.save()
                log_visit_action(self.object, 'COMPLETED', by_user=request.user, remarks=remarks)
                
            elif action == 'TRANSFERRED':
                if target_desk:
                     old_desk = self.object.current_desk
                     self.object.current_desk = target_desk
                     self.object.status = Visit.Status.ROUTED
                     self.object.save()
                     log_visit_action(self.object, 'TRANSFERRED', by_user=request.user, remarks=remarks, from_desk=old_desk, to_desk=target_desk)
            
            elif action == 'ROUTED':
                if target_desk:
                     self.object.current_desk = target_desk
                     self.object.status = Visit.Status.ROUTED
                     self.object.save()
                     log_visit_action(self.object, 'ASSIGNED', by_user=request.user, remarks=remarks, to_desk=target_desk)

            elif action == 'COMMENT':
                log_visit_action(self.object, 'COMMENT', by_user=request.user, remarks=remarks)
                
            return redirect('visit_regn:visit_detail', pk=self.object.pk)
            
        # If invalid, re-render
        context = self.get_context_data()
        context['action_form'] = form
        return self.render_to_response(context)
