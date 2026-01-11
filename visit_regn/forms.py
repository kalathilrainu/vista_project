from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Visit

class VisitRegistrationForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ['name', 'mobile', 'purpose', 'reference_number']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Your Name / പേര്')}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Mobile Number / മൊബൈൽ നമ്പർ')}),
            'purpose': forms.Select(attrs={'class': 'form-select'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Reference Number (Optional) / റഫറൻസ് നമ്പർ')}),
        }
        labels = {
            'name': _('Name / പേര്'),
            'mobile': _('Mobile / മൊബൈൽ'),
            'purpose': _('Purpose / ആവശ്യം'),
            'reference_number': _('Reference Number / റഫറൻസ് നമ്പർ'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mobile'].required = True

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        if mobile:
            if not mobile.isdigit():
                 raise forms.ValidationError(_("Mobile number must contain only digits."))
            
            if len(mobile) != 10:
                raise forms.ValidationError(_("Mobile number must be exactly 10 digits."))
        return mobile

class QuickRegisterForm(forms.Form):
    pass

class VisitActionForm(forms.Form):
    action_choices = [
        ('ATTENDED', _('Mark Attended')),
        ('COMPLETED', _('Mark Completed')),
        ('TRANSFERRED', _('Transfer')),
        ('COMMENT', _('Add Comment')),
        ('ROUTED', _('Assign Desk')),
    ]
    
    action = forms.ChoiceField(choices=action_choices, widget=forms.RadioSelect)
    remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}))
    target_desk = forms.ModelChoiceField(queryset=None, required=False, label=_('To Desk (for Transfer/Routing)'))

    def __init__(self, *args, **kwargs):
        desks = kwargs.pop('desks', None)
        super().__init__(*args, **kwargs)
        if desks is not None:
             self.fields['target_desk'].queryset = desks

class VisitStaffUpdateForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ['name', 'mobile', 'purpose', 'reference_number']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'purpose': forms.Select(attrs={'class': 'form-select'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Visitor Name',
            'mobile': 'Mobile Number',
            'purpose': 'Purpose',
            'reference_number': 'Reference Number',
        }

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        if mobile:
            if not mobile.isdigit():
                 raise forms.ValidationError(_("Mobile number must contain only digits."))
            # Relaxed validation for staff editing (maybe they entered a partial number or it's a landline?)
            # Keeping 10 digits for now but making specific note:
            if len(mobile) != 10:
                # If staff needs to enter non-standard, we might need to remove this. 
                # For now, strict is safer.
                raise forms.ValidationError(_("Mobile number must be exactly 10 digits."))
        return mobile
