from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import User, StaffMember, UserAssignment, Office, Desk

class UserAssignmentForm(forms.ModelForm):
    class Meta:
        model = UserAssignment
        fields = ('user', 'staff_member', 'from_date', 'to_date')
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'staff_member': forms.Select(attrs={'class': 'form-select'}),
            'from_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'to_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class CustomUserCreationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'role', 'office', 'desk')
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'office': forms.Select(attrs={'class': 'form-select'}),
            'desk': forms.Select(attrs={'class': 'form-select'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'placeholder': 'Auto-generated'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].required = False
        self.fields['desk'].queryset = Desk.objects.none()
        self.fields['desk'].required = False

        if 'office' in self.data:
            try:
                office_id = int(self.data.get('office'))
                self.fields['desk'].queryset = Desk.objects.filter(office_id=office_id).order_by('name')
            except (ValueError, TypeError):
                pass

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password("Vista@123")
        if commit:
            user.save()
        return user

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('username', 'role', 'office', 'desk', 'is_active')
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'office': forms.Select(attrs={'class': 'form-select'}),
            'desk': forms.Select(attrs={'class': 'form-select'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['desk'].queryset = Desk.objects.none()
        self.fields['desk'].required = False

        if 'office' in self.data:
            try:
                office_id = int(self.data.get('office'))
                self.fields['desk'].queryset = Desk.objects.filter(office_id=office_id).order_by('name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.office:
            self.fields['desk'].queryset = self.instance.office.desks.order_by('name')

class OfficeForm(forms.ModelForm):
    class Meta:
        model = Office
        fields = ('name', 'code')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
        }

class DeskForm(forms.ModelForm):
    class Meta:
        model = Desk
        fields = ('name', 'office')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'office': forms.Select(attrs={'class': 'form-select'}),
        }
class StaffMemberForm(forms.ModelForm):
    class Meta:
        model = StaffMember
        fields = ('pen', 'name', 'designation', 'office', 'date_of_joining', 'date_of_transfer', 'is_active')
        widgets = {
            'pen': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'designation': forms.TextInput(attrs={'class': 'form-control'}),
            'office': forms.Select(attrs={'class': 'form-select'}),
            'date_of_joining': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_of_transfer': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CaptchaLoginForm(AuthenticationForm):
    captcha = forms.IntegerField(
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Answer', 'autocomplete': 'off'}),
        label="Math Captcha"
    )

    def clean_captcha(self):
        captcha = self.cleaned_data.get('captcha')
        expected = self.request.session.get('captcha_expected')
        
        if expected is None:
             # Session might have expired or direct post without page load
             # In a strict sense, we could error, but let's just error to be safe.
             raise ValidationError("Session expired. Please refresh the page.")
        
        if int(captcha) != int(expected):
            raise ValidationError("Incorrect answer. Please try again.")
        
        return captcha

