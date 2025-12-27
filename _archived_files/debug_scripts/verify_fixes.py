import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case

# Get Case #28
case = Case.objects.get(id=28)

print("="*90)
print("TESTING THE FIXES - CASE #28")
print("="*90)

# Check critical fields that were missing before
critical_checks = {
    'FEHB Y/N/Unsure': {
        'section': 'fehb',
        'fields': ['five_year_requirement', 'keep_in_retirement', 'spouse_reliant']
    },
    'FLTCIP discuss_options': {
        'section': 'fltcip',
        'fields': ['discuss_options']
    },
    'TSP questions': {
        'section': 'tsp',
        'fields': ['sole_source', 'in_service_withdrawal']
    },
    'FEGLI': {
        'section': 'fegli',
        'fields': ['premium_1', 'premium_2', 'premium_3', 'premium_4', 'five_year_requirement', 'keep_in_retirement', 'sole_source']
    }
}

data = case.fact_finder_data or {}

for category, info in critical_checks.items():
    section_data = data.get(info['section'], {})
    print(f"\n{category}:")
    print("-" * 90)
    
    for field in info['fields']:
        value = section_data.get(field, 'MISSING')
        if value and value != '':
            print(f"  ✅ {field}: {repr(value)}")
        else:
            print(f"  ❌ {field}: {repr(value)}")

print("\n" + "="*90)
print("VERDICT: " + ("🎉 FIXED! All critical fields are now being captured!" if all(
    data.get(info['section'], {}).get(field) for category, info in critical_checks.items() for field in info['fields']
) else "⚠️  Some fields still missing - needs more investigation"))
print("="*90)
