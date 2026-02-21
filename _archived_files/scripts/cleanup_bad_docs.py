#!/usr/bin/env python
"""Delete malformed documents 170 and 171"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import CaseDocument

# Get and delete document 170
doc170 = CaseDocument.objects.get(id=170)
print("Deleting document 170: {}".format(doc170.original_filename))
print("  File field: '{}'".format(doc170.file))
print("  Document type: {}".format(doc170.document_type))

# Try to delete the actual file if it exists
if doc170.file:
    try:
        doc170.file.delete()
        print("  Deleted file from storage")
    except Exception as e:
        print("  Error deleting file: {}".format(e))

doc170.delete()
print("  ✓ Document 170 deleted from database")
print()

# Get and delete document 171
doc171 = CaseDocument.objects.get(id=171)
print("Deleting document 171: {}".format(doc171.original_filename))
print("  File field: '{}'".format(doc171.file))
print("  Document type: {}".format(doc171.document_type))

# Try to delete the actual file if it exists
if doc171.file:
    try:
        doc171.file.delete()
        print("  Deleted file from storage")
    except Exception as e:
        print("  Error deleting file: {}".format(e))

doc171.delete()
print("  ✓ Document 171 deleted from database")
print()

print("Cleanup complete. Remaining documents for case 66:")
remaining = CaseDocument.objects.filter(case__id=66).all()
for doc in remaining:
    print("  - ID: {} | {} | {}".format(doc.id, doc.original_filename, doc.document_type))
