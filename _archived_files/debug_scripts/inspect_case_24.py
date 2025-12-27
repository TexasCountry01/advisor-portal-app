import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case

try:
    case = Case.objects.get(id=24)
    print("=" * 80)
    print(f"CASE 24 FACT FINDER DATA INSPECTION")
    print("=" * 80)
    
    # Get all top-level keys
    print("\n### TOP-LEVEL SECTIONS ###")
    sections = list(case.fact_finder_data.keys())
    print(f"Sections found: {sections}")
    print(f"Total sections: {len(sections)}\n")
    
    # Inspect each section
    for section in sections:
        data = case.fact_finder_data.get(section, {})
        if isinstance(data, dict):
            print(f"\n### {section.upper()} ({len(data)} fields) ###")
            # Show first 10 fields as sample
            for i, (key, value) in enumerate(list(data.items())[:10]):
                print(f"  {key}: {value}")
            if len(data) > 10:
                print(f"  ... and {len(data) - 10} more fields")
        else:
            print(f"\n### {section.upper()} ###")
            print(f"  {data}")
    
    # Full JSON dump to file
    with open('case_24_full_data.json', 'w') as f:
        json.dump(case.fact_finder_data, f, indent=2)
    
    print(f"\n\n{'=' * 80}")
    print(f"Full data saved to: case_24_full_data.json")
    print(f"{'=' * 80}")
    
except Case.DoesNotExist:
    print("Case 24 not found!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
