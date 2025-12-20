from django import forms
from .models import CaseDocument, CaseReport, CaseNote


class CaseDocumentForm(forms.ModelForm):
    """Form for uploading case documents"""
    
    class Meta:
        model = CaseDocument
        fields = ['document_type', 'file', 'notes']
        widgets = {
            'document_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional: Add notes about this document',
            }),
        }
        labels = {
            'document_type': 'Document Type',
            'file': 'Select File',
            'notes': 'Notes (Optional)',
        }


class CaseReportForm(forms.ModelForm):
    """Form for uploading case reports"""
    
    class Meta:
        model = CaseReport
        fields = ['report_file']
        widgets = {
            'report_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf',
            }),
        }
        labels = {
            'report_file': 'Select PDF File',
        }


class CaseNoteForm(forms.ModelForm):
    """Form for adding case notes"""
    
    class Meta:
        model = CaseNote
        fields = ['note']
        widgets = {
            'note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter note details...',
            }),
        }
        labels = {
            'note': 'Note',
        }
