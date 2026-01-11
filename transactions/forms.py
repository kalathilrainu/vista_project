from django import forms
from .models import Transaction

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['block', 'tp_number', 'remarks1', 'remarks2', 'remarks3']
        widgets = {
            'block': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Block', 'maxlength': '4'}),
            'tp_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Thandaper No', 'maxlength': '5'}),
            'remarks1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Remarks 1'}),
            'remarks2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Remarks 2'}),
            'remarks3': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Remarks 3'}),
        }
