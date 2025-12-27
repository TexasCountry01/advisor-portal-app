#!/usr/bin/env python
"""
Fix remaining academy, non_deduction, break_in_service, and part_time fields.
"""

from pathlib import Path

pdf_path = Path('cases/templates/cases/fact_finder_pdf_template_v2.html')
template = pdf_path.read_text()

# These fields belong to their own sections, not fact_finder
replacements = {
    'fact_finder.academy_': 'academy.',
    'fact_finder.non_deduction_': 'non_deduction.',
    'fact_finder.break_': 'break_service.',
    'fact_finder.part_time_': 'part_time.',
}

print("="*120)
print("FIXING REMAINING SERVICE SECTION VARIABLES")
print("="*120)

for old, new in replacements.items():
    count = template.count(old)
    if count > 0:
        print(f"Replacing {count:2d}x: {old:40s} → {new}")
        template = template.replace(old, new)

pdf_path.write_text(template)

print("\n✅ All service section variables fixed!")
