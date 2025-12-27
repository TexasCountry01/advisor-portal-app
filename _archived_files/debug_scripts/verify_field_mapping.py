"""
Verify that all form fields are captured in views.py
"""
import re

# Read all form field names
with open('all_form_fields.txt', 'r') as f:
    form_fields = [line.strip() for line in f if line.strip() and not line.startswith('$')]

# Read views.py
with open('cases/views.py', 'r', encoding='utf-8') as f:
    views_content = f.read()

# Find all request.POST.get() calls in views.py
post_gets = re.findall(r"request\.POST\.get\('([^']+)'", views_content)

# Find fields that are NOT captured
missing_fields = []
for field in form_fields:
    if field not in post_gets:
        missing_fields.append(field)

print(f"Total form fields: {len(form_fields)}")
print(f"Fields captured in views.py: {len(post_gets)}")
print(f"Missing fields: {len(missing_fields)}\n")

if missing_fields:
    print("MISSING FIELDS:")
    for field in sorted(missing_fields):
        print(f"  - {field}")
else:
    print("✅ All fields are captured!")
