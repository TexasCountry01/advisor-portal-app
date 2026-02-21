#!/usr/bin/env python
"""
Fix all remaining document type issues in the database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import CaseDocument

# Fix all old document types
updates = {
    'Federal Fact Finder': 'fact_finder',
    'Supporting Document': 'supporting',
}

for old_type, new_type in updates.items():
    count = CaseDocument.objects.filter(document_type=old_type).update(document_type=new_type)
    if count > 0:
        print(f"Updated {count} documents from '{old_type}' to '{new_type}'")

print("\n=== Updated Document Type Summary ===\n")
from django.db.models import Count
doc_types = CaseDocument.objects.values('document_type').annotate(count=Count('id')).order_by('-count')
for dt in doc_types:
    print(f"{dt['document_type']}: {dt['count']} documents")
