#!/usr/bin/env python
"""Remove test documents from TEST server"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import CaseDocument

print("Cleaning up test documents...")
print("=" * 60)

# Find and delete test documents
test_docs = CaseDocument.objects.filter(
    original_filename__in=[
        'DIAGNOSTIC_FILE_TEST.txt',
        'Brooks_Test_Document_from_Member.pdf'
    ]
)

print("Found {} test documents to remove".format(test_docs.count()))
print()

for doc in test_docs:
    print("Deleting: {} (ID: {})".format(doc.original_filename, doc.id))
    
    # Delete file from storage
    if doc.file:
        try:
            doc.file.delete()
            print("  ✓ File deleted from disk")
        except Exception as e:
            print("  ✗ Error deleting file: {}".format(e))
    
    # Delete database record
    doc.delete()
    print("  ✓ Record deleted from database")
    print()

print("=" * 60)
print("Cleanup complete!")

# Verify no test documents remain
remaining = CaseDocument.objects.filter(case__id=66).all()
print()
print("Remaining documents for case 66 (Garth Brooks):")
if remaining.count() == 0:
    print("  (none - case is clean)")
else:
    for doc in remaining:
        print("  - ID: {} | {}".format(doc.id, doc.original_filename))
