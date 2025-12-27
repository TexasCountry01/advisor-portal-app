"""
Fill the ProFeds Federal Fact Finder PDF with case data.
Uses the official template PDF with 209 fillable form fields.
"""
import os
import io
import django
from PyPDF2 import PdfReader, PdfWriter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case

def fill_pdf_from_template(case_id, template_path='reference_PDF.pdf', output_name=None):
    """
    Fill the official ProFeds PDF template with case data.
    This is much better than recreating the layout - we use the actual template.
    """
    try:
        case = Case.objects.get(id=case_id)
        data = case.fact_finder_data or {}
        
        # Read template
        reader = PdfReader(template_path)
        writer = PdfWriter()
        
        # Create field value mapping based on our data
        field_values = {}
        
        # Basic Information (Page 1)
        bi = data.get('basic_information', {})
        field_values.update({
            'A 1': bi.get('employee_name', ''),
            'A 2': bi.get('spouse_name', ''),
            'A 3': bi.get('address', ''),
            'A 4': bi.get('dob', ''),
        })
        
        # Retirement System Checkboxes
        rs = data.get('retirement_system', '')
        field_values.update({
            'B 1': 'Yes' if rs == 'CSRS' else '',
            'B 2': 'Yes' if rs == 'CSRS Offset' else '',
            'B 3': 'Yes' if rs == 'FERS' else '',
            'B 4': 'Yes' if rs == 'FERS Transfer' else '',
        })
        
        # Employee Type Checkboxes
        et = data.get('employee_type', '')
        field_values.update({
            'B 5': 'Yes' if et == 'Regular' else '',
            'B 6': 'Yes' if et == 'Offset' else '',
            'B 7': 'Yes' if et == 'Postal Worker' else '',
            'B 8': 'Yes' if et == 'Unsure' else '',
        })
        
        # Military Active Duty
        mad = data.get('mad', {})
        field_values.update({
            'C 2': mad.get('notes', ''),
        })
        
        # Try to fill the PDF
        total_filled = 0
        empty_fields = []
        
        # Get the form AcroForm
        root = reader.trailer['/Root'].get_object() if hasattr(reader.trailer['/Root'], 'get_object') else reader.trailer['/Root']
        acro_form = root.get('/AcroForm')
        if not acro_form:
            print("ERROR: PDF doesn't have form fields")
            return None
        
        # Resolve the indirect reference
        if hasattr(acro_form, 'get_object'):
            acro_form = acro_form.get_object()
            
        # Get all fields
        fields_list = acro_form.get('/Fields', [])
        
        for field_ref in fields_list:
            field_obj = field_ref.get_object()
            field_name = field_obj.get('/T', '')
            
            if field_name in field_values:
                value = field_values[field_name]
                if value:
                    field_obj.update({
                        '/V': value,
                        '/AS': value
                    })
                    total_filled += 1
            else:
                empty_fields.append(field_name)
        
        # Copy pages to writer
        for page in reader.pages:
            writer.add_page(page)
        
        # Update form for filling
        writer.update_page_form_field_state(writer.pages[0], field_values)
        
        # Save output
        if not output_name:
            output_name = f'case_{case_id}_from_template.pdf'
        
        output_path = output_name
        with open(output_path, 'wb') as f:
            writer.write(f)
        
        print(f"[SUCCESS] PDF Generated from Template!")
        print(f"   File: {output_name}")
        print(f"   Size: {os.path.getsize(output_path):,} bytes")
        print(f"   Fields Filled: {total_filled}/209")
        print(f"\n   Note: This uses the official ProFeds template directly.")
        print(f"   Layout will match exactly with the reference PDF.")
        
        return output_name
        
    except Case.DoesNotExist:
        print(f"Case {case_id} not found")
        return None
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    fill_pdf_from_template(29)
