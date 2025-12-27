from django import forms
from .models import CaseDocument


class CaseDocumentForm(forms.ModelForm):
    """Form for uploading case documents"""
    
    class Meta:
        model = CaseDocument
        fields = ['document_type', 'file']
        widgets = {
            'document_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }
