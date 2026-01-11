from django import forms
from .models import OfficeFile, DocumentSubmission

class OfficeFileForm(forms.ModelForm):
    class Meta:
        model = OfficeFile
        fields = ['status', 'interim_status', 'fee_receipt_no', 'fee_receipt_date', 
                  'reply_to', 'reply_date', 'reply_type', 'despatch_mode', 'despatch_id',
                  'remarks1', 'remarks2', 'remarks3']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'interim_status': forms.Select(attrs={'class': 'form-select'}),
            'fee_receipt_no': forms.TextInput(attrs={'class': 'form-control'}),
            'fee_receipt_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reply_to': forms.TextInput(attrs={'class': 'form-control'}),
            'reply_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reply_type': forms.Select(attrs={'class': 'form-select'}),
            'despatch_mode': forms.Select(attrs={'class': 'form-select'}),
            'despatch_id': forms.TextInput(attrs={'class': 'form-control'}),
            'remarks1': forms.TextInput(attrs={'class': 'form-control'}),
            'remarks2': forms.TextInput(attrs={'class': 'form-control'}),
            'remarks3': forms.TextInput(attrs={'class': 'form-control'}),
        }

class DocumentSubmissionForm(forms.ModelForm):
    class Meta:
        model = DocumentSubmission
        fields = ['papers_submitted']
        widgets = {
            'papers_submitted': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'List the papers submitted...'}),
        }
