#!/usr/bin/env python
"""
Fix all PDF template variable mismatches by replacing fact_finder.* with correct nested section references.
"""

import re
from pathlib import Path

pdf_path = Path('cases/templates/cases/fact_finder_pdf_template_v2.html')
template = pdf_path.read_text()

# Define all replacements
# fact_finder.* prefix replacements
replacements = {
    # Military active duty fields
    'fact_finder.active_duty_': 'mad.',
    'fact_finder.reserves_': 'reserves.',
    
    # Financial/leave fields that belong to add_info
    'fact_finder.leave_scd': 'add_info.leave_scd',
    'fact_finder.retirement_scd': 'add_info.retirement_scd',
    'fact_finder.retirement_age': 'add_info.retirement_age',
    'fact_finder.retirement_date': 'add_info.retirement_date',
    'fact_finder.spousal_pension_reduction_reason': 'add_info.spousal_pension_reduction_reason',
    'fact_finder.current_annual_salary': 'add_info.current_annual_salary',
    'fact_finder.sick_leave_hours': 'add_info.sick_leave_hours',
    'fact_finder.annual_leave_hours': 'add_info.annual_leave_hours',
    'fact_finder.ss_benefit_at_62': 'add_info.ss_benefit_at_62',
    'fact_finder.ss_desired_start_age': 'add_info.ss_desired_start_age',
    'fact_finder.ss_benefit_at_desired_age': 'add_info.ss_benefit_at_desired_age',
    'fact_finder.page1_notes': 'add_info.page1_notes',
    'fact_finder.active_duty_notes': 'mad.notes',
}

print("="*120)
print("PDF TEMPLATE VARIABLE REPLACEMENT")
print("="*120)

# Apply replacements
for old, new in replacements.items():
    count = template.count(old)
    if count > 0:
        print(f"Replacing {count:2d}x: {old:50s} → {new}")
        template = template.replace(old, new)

# Save the fixed template
pdf_path.write_text(template)

print("\n✅ Template fixed successfully!")
print(f"\nFile saved: {pdf_path}")
