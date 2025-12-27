import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case

# Get Case #27
case = Case.objects.get(id=27)

print("="*70)
print("CASE #27 FACT FINDER DATA ANALYSIS")
print("="*70)

# Check if fact_finder_data exists
if case.fact_finder_data:
    print("\n✓ fact_finder_data JSON exists\n")
    
    # Pretty print the entire structure
    print(json.dumps(case.fact_finder_data, indent=2))
    
    print("\n" + "="*70)
    print("SECTION-BY-SECTION CHECK:")
    print("="*70)
    
    # Check each major section
    sections = [
        'basic_information',
        'retirement_information',
        'pay_leave_information', 
        'military_service',
        'non_deduction_service',
        'break_in_service',
        'part_time_service',
        'fegli',
        'fehb',
        'fltcip',
        'tsp',
        'additional_notes'
    ]
    
    for section in sections:
        if section in case.fact_finder_data:
            print(f"\n✓ {section.upper()}: {len(case.fact_finder_data[section])} fields")
        else:
            print(f"\n✗ {section.upper()}: MISSING")
            
else:
    print("\n✗ NO fact_finder_data - data not submitted properly!")
