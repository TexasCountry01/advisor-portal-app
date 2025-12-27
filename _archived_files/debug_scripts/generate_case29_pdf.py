#!/usr/bin/env python
"""
Generate PDF for Case #29 and verify the template fixes worked.
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case
from cases.services.pdf_generator import generate_fact_finder_pdf

try:
    # Get Case #29 (by ID)
    case = Case.objects.get(id=29)
    print(f"Found Case ID {case.id}: {case.employee_first_name} {case.employee_last_name}")
    
    # Generate PDF
    result = generate_fact_finder_pdf(case)
    
    # Get the PDF bytes from the CaseDocument
    if result:
        pdf_bytes = result.file.read()
    else:
        print("ERROR: PDF generation returned None - WeasyPrint might not be available")
        exit(1)
    
    # Save to disk
    output_path = 'case_29_FIXED_TEST.pdf'
    with open(output_path, 'wb') as f:
        f.write(pdf_bytes)
    
    print("[SUCCESS] PDF Generated Successfully!")
    print(f"   File: {output_path}")
    print(f"   Size: {len(pdf_bytes):,} bytes")
    print("")
    print("   You can now view the PDF to verify all fields are rendering.")
    print("   Look for:")
    print("   - Military Active Duty section with notes")
    print("   - Military Reserves section")
    print("   - Academy section with notes")
    print("   - Part-Time section with notes")
    print("   - Break in Service section with notes")
    print("   - Non-Deduction Service section with notes")
    
except Case.DoesNotExist:
    print("ERROR: Case #29 not found. Please create it first.")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
