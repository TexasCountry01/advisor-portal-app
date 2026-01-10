#!/usr/bin/env python
"""
Clean up all cases from LOCAL database
This will delete all cases and their related documents, reports, and notes due to CASCADE delete settings
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case, CaseDocument, CaseReport, CaseNote, APICallLog

# Show counts before deletion
print("\n=== BEFORE CLEANUP ===\n")
case_count = Case.objects.count()
doc_count = CaseDocument.objects.count()
report_count = CaseReport.objects.count()
note_count = CaseNote.objects.count()
api_log_count = APICallLog.objects.count()

print(f"Cases: {case_count}")
print(f"Documents: {doc_count}")
print(f"Reports: {report_count}")
print(f"Notes: {note_count}")
print(f"API Logs: {api_log_count}")

total_before = case_count + doc_count + report_count + note_count + api_log_count

if total_before == 0:
    print("\n✓ Database is already clean - no cases to delete")
else:
    # Confirm deletion
    response = input(f"\n⚠️ This will delete {case_count} cases and all {doc_count + report_count + note_count} related records. Continue? (yes/no): ")
    
    if response.lower() == 'yes':
        # Delete all cases (cascade will handle related records)
        deleted_cases, _ = Case.objects.all().delete()
        
        print(f"\n✓ Deleted {deleted_cases} case records (including cascaded deletions)")
        
        # Show counts after deletion
        print("\n=== AFTER CLEANUP ===\n")
        print(f"Cases: {Case.objects.count()}")
        print(f"Documents: {CaseDocument.objects.count()}")
        print(f"Reports: {CaseReport.objects.count()}")
        print(f"Notes: {CaseNote.objects.count()}")
        print(f"API Logs: {APICallLog.objects.count()}")
        
        print("\n✓ LOCAL database cleanup complete! Ready to start fresh.")
    else:
        print("\n✗ Cleanup cancelled - no changes made")
