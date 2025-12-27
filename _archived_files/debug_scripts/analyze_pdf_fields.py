"""
Map case data to ProFeds Federal Fact Finder PDF form fields.
This provides a mapping between our database fields and the PDF template fields.
"""

# Field mapping: Our database field -> PDF form field name
# This will be populated by analyzing the template PDF more carefully
FIELD_MAPPING = {
    # Basic Information
    'employee_name': 'Employee Name',  # Will refine after testing
    'spouse_name': 'Spouse Name',
    'dob': 'Date of Birth',
    
    # Checkboxes
    'retirement_system_csrs': 'CSRS',
    'retirement_system_fers': 'FERS',
    'retirement_system_csrs_offset': 'CSRS Offset',
    'retirement_system_fers_transfer': 'FERS Transfer',
    
    'employee_type_regular': 'Employee Type Regular',
    'employee_type_postal': 'Employee Type Postal',
    'employee_type_offset': 'Employee Type Offset',
}

def get_field_name_from_type(field_obj):
    """Extract field name and type from a PDF field object"""
    name = field_obj.get('/T', 'Unknown')
    field_type = field_obj.get('/FT', 'Unknown')
    return name, field_type

def analyze_pdf_fields(pdf_path='reference_PDF.pdf'):
    """
    Analyze all fields in the PDF to understand the structure.
    """
    from PyPDF2 import PdfReader
    
    reader = PdfReader(pdf_path)
    acro_form = reader.trailer['/Root']['/AcroForm']
    fields = {}
    
    if '/Fields' in acro_form:
        for field_ref in acro_form['/Fields']:
            field = field_ref.get_object()
            field_name = field.get('/T', '')
            if field_name:
                field_type = field.get('/FT', 'Unknown')
                fields[field_name] = {
                    'type': field_type,
                    'field_obj': field
                }
    
    # Group by type
    by_type = {}
    for name, info in fields.items():
        ftype = info['type']
        if ftype not in by_type:
            by_type[ftype] = []
        by_type[ftype].append(name)
    
    print("PDF FIELD ANALYSIS")
    print("=" * 60)
    for ftype, names in sorted(by_type.items()):
        print(f"\n{ftype} Fields ({len(names)}):")
        for i, name in enumerate(sorted(names)[:20]):
            print(f"  {i+1}. {name}")
        if len(names) > 20:
            print(f"  ... and {len(names) - 20} more")
    
    return fields

if __name__ == '__main__':
    analyze_pdf_fields()
