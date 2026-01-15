from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, CreateView, UpdateView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Q
from .models import User, StaffMember, UserAssignment, LoginSession, Office, Desk
from .forms import CustomUserCreationForm, CustomUserChangeForm, StaffMemberForm, UserAssignmentForm, OfficeForm, DeskForm, CaptchaLoginForm
from .utils import get_current_staff_for_user
from django.contrib.auth.views import LoginView
from django.conf import settings





class LandingLoginView(LoginView):
    authentication_form = CaptchaLoginForm
    redirect_authenticated_user = True

    template_name = 'home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Generate Simple Math CAPTCHA
        import random
        
        num1 = random.randint(1, 9)
        num2 = random.randint(1, 9)
        # Using addition only for simplicity and mobile-friendliness
        question = f"What is {num1} + {num2}?"
        answer = num1 + num2
        
        self.request.session['captcha_expected'] = answer
        context['captcha_question'] = question

        # Add basic announcements content required by home.html
        context['announcements'] = [
            'Village Office working hours: 10 AM - 5 PM',
            'SIR 2026 – Hearing Time: 9 AM - 5 PM',
            'Voter Help Desk Working at Village Office'
        ]
        return context

    def get_success_url(self):
        user = self.request.user
        
        # Check for Kiosk Users (VS prefix) who have a valid office assigned
        if user.office and user.username.startswith('VS'):
            return reverse_lazy('visit_regn:kiosk_home')
        
        return super().get_success_url()

@login_required
def user_management(request):
    """
    Landing page for User Management Module.
    """
    return render(request, 'accounts/management.html')

class StaffMemberListView(LoginRequiredMixin, ListView):
    model = StaffMember
    template_name = 'accounts/staff_list.html'
    context_object_name = 'staff_members'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(pen__icontains=query) |
                Q(designation__icontains=query)
            )
        return queryset

class StaffMemberCreateView(LoginRequiredMixin, CreateView):
    model = StaffMember
    form_class = StaffMemberForm
    template_name = 'accounts/staff_form.html'
    success_url = reverse_lazy('staff_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Staff Member'
        return context

class StaffMemberUpdateView(LoginRequiredMixin, UpdateView):
    model = StaffMember
    form_class = StaffMemberForm
    template_name = 'accounts/staff_form.html'
    success_url = reverse_lazy('staff_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Staff Member'
        return context

class UserAssignmentListView(LoginRequiredMixin, ListView):
    model = UserAssignment
    template_name = 'accounts/userassignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(user__username__icontains=query) |
                Q(staff_member__name__icontains=query)
            )
        return queryset

class UserAssignmentCreateView(LoginRequiredMixin, CreateView):
    model = UserAssignment
    form_class = UserAssignmentForm
    template_name = 'accounts/userassignment_form.html'
    success_url = reverse_lazy('userassignment_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New Assignment'
        return context

class UserAssignmentUpdateView(LoginRequiredMixin, UpdateView):
    model = UserAssignment
    form_class = UserAssignmentForm
    template_name = 'accounts/userassignment_form.html'
    success_url = reverse_lazy('userassignment_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Assignment'
        return context

class LoginSessionListView(LoginRequiredMixin, ListView):
    model = LoginSession
    template_name = 'accounts/loginsession_list.html'
    context_object_name = 'sessions'
    paginate_by = 25
    ordering = ['-login_time']

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(user__username__icontains=query) |
                Q(ip_address__icontains=query)
            )
        return queryset

def load_desks(request):
    office_id = request.GET.get('office')
    if not office_id:
        return JsonResponse([], safe=False)
    desks = Desk.objects.filter(office_id=office_id).order_by('name')
    return JsonResponse(list(desks.values('id', 'name')), safe=False)

class UserListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(username__icontains=query) | 
                Q(first_name__icontains=query) | 
                Q(email__icontains=query)
            )
        return queryset

class UserCreateView(LoginRequiredMixin, CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('user_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New User'
        return context

    def form_invalid(self, form):
        print("User Creation Form Errors:", form.errors)
        return super().form_invalid(form)

    def form_valid(self, form):
        user = form.save(commit=False)
        
        # Generate username if office is selected
        if user.office:
            from .utils import generate_username
            user.username = generate_username(user.role, user.office.code)
        
        user.save()
        messages.success(self.request, f"User created successfully! Username: {user.username}")
        return super(UserCreateView, self).form_valid(form)

class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = CustomUserChangeForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('user_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit User'
        return context

@login_required
def who_am_i(request):
    user = request.user
    staff = get_current_staff_for_user(user)
    
    data = {
        "username": user.username,
        "role": user.role,
        "office": str(user.office) if user.office else None,
        "desk": str(user.desk) if user.desk else None,
        "staff_member": {
            "pen": staff.pen,
            "name": staff.name,
            "designation": staff.designation
        } if staff else None
    }
    return JsonResponse(data)

# Office Management Views
class OfficeListView(LoginRequiredMixin, ListView):
    model = Office
    template_name = 'accounts/office_list.html'
    context_object_name = 'offices'
    paginate_by = 10

class OfficeCreateView(LoginRequiredMixin, CreateView):
    model = Office
    form_class = OfficeForm
    template_name = 'accounts/office_form.html'
    success_url = reverse_lazy('office_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New Office'
        return context

class OfficeUpdateView(LoginRequiredMixin, UpdateView):
    model = Office
    form_class = OfficeForm
    template_name = 'accounts/office_form.html'
    success_url = reverse_lazy('office_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Office'
        return context

# Desk Management Views
class DeskListView(LoginRequiredMixin, ListView):
    model = Desk
    template_name = 'accounts/desk_list.html'
    context_object_name = 'desks'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(office__name__icontains=query)
            )
        return queryset

class DeskCreateView(LoginRequiredMixin, CreateView):
    model = Desk
    form_class = DeskForm
    template_name = 'accounts/desk_form.html'
    success_url = reverse_lazy('desk_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New Desk'
        return context

class DeskUpdateView(LoginRequiredMixin, UpdateView):
    model = Desk
    form_class = DeskForm
    template_name = 'accounts/desk_form.html'
    success_url = reverse_lazy('desk_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Desk'
        return context
