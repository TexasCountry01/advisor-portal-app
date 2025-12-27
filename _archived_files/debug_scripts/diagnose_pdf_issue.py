import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case

# Get Case #27
case = Case.objects.get(id=27)
data = case.fact_finder_data

print("FEHB Section in JSON:")
print(json.dumps(data.get('fehb', {}), indent=2))

print("\n" + "="*70)
print("FLTCIP Section in JSON:")
print(json.dumps(data.get('fltcip', {}), indent=2))

print("\n" + "="*70)
print("ADDITIONAL NOTES in JSON:")
print("add_info.additional_notes:", data.get('add_info', {}).get('additional_notes', 'NOT FOUND'))

print("\n" + "="*70)
print("\nPDF template expects these field names (from FederalFactFinder model):")
print("  fehb_health_premium (not fehb.health_premium)")
print("  fehb_dental_premium")
print("  fehb_vision_premium")
print("  etc.")

print("\nBut JSON has:")
print("  fehb.health_premium")
print("  fehb.dental_premium")  
print("  fehb.vision_premium")
print("  etc.")

print("\n" + "="*70)
print("SOLUTION: PDF template needs to use correct JSON paths")
print("  Change: {{ fact_finder.fehb_health_premium }}")
print("  To: {{ fehb.health_premium }}")
