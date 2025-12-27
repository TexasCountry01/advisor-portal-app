import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case, CaseDocument

# Get Case #27
case = Case.objects.get(id=27)

# Delete old PDF
old_pdfs = CaseDocument.objects.filter(case=case, document_type='fact_finder')
print(f"Deleting {old_pdfs.count()} old PDF(s)...")
old_pdfs.delete()

# Reset PDF status
case.fact_finder_pdf_status = 'pending'
case.save(update_fields=['fact_finder_pdf_status'])

print("✓ Cleared old PDF")
print("  Next time you view the case, the PDF will be regenerated with the fixed template")
print("  Go to: http://127.0.0.1:8000/cases/27/fact-finder-pdf/")
