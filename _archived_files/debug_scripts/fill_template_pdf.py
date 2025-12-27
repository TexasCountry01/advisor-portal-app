"""
Fill the ProFeds Federal Fact Finder PDF template with case data.
This uses the official template PDF with fillable form fields.
"""
import os
import django
from PyPDF2 import PdfReader, PdfWriter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case

def fill_pdf_template(case_id, template_path='reference_PDF.pdf'):
    """
    Fill the PDF template with case data.
    """
    try:
        case = Case.objects.get(id=case_id)
        data = case.fact_finder_data or {}
        
        # Read the template PDF
        reader = PdfReader(template_path)
        writer = PdfWriter()
        
        # Get form field information
        if '/AcroForm' not in reader.trailer['/Root']:
            print("ERROR: Template PDF doesn't have form fields")
            return None
        
        acro_form = reader.trailer['/Root']['/AcroForm']
        fields = {}
        
        # Build a map of field names
        if '/Fields' in acro_form:
            for field_ref in acro_form['/Fields']:
                field = field_ref.get_object()
                field_name = field.get('/T', '')
                if field_name:
                    fields[field_name] = field
        
        print(f"Found {len(fields)} form fields in template")
        print(f"\nFirst 15 field names:")
        for i, name in enumerate(list(fields.keys())[:15]):
            print(f"  {i+1}. {name}")
        
        if len(fields) > 15:
            print(f"  ... and {len(fields) - 15} more")
        
        return len(fields)
        
    except Case.DoesNotExist:
        print(f"Case {case_id} not found")
        return None
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    result = fill_pdf_template(29)
    if result:
        print(f"\nTemplate has {result} fields available to fill")
