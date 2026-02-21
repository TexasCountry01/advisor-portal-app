#!/usr/bin/env python
"""
Diagnostic script to check case documents in the database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case, CaseDocument

# Get the most recent cases
recent_cases = Case.objects.order_by('-created_at')[:5]

print("\n=== Recent Cases ===\n")
for case in recent_cases:
    print(f"Case ID: {case.id}, External ID: {case.external_case_id}, Status: {case.status}, Created: {case.created_at}")
    
    # Get documents for this case
    documents = CaseDocument.objects.filter(case=case)
    print(f"  Documents ({documents.count()}):")
    for doc in documents:
        print(f"    - Type: {doc.document_type}, File: {doc.original_filename}, Uploaded: {doc.uploaded_at}")
    print()

# Also check for any duplicate documents
print("\n=== Document Type Summary ===\n")
doc_types = CaseDocument.objects.values('document_type').distinct()
for dt in doc_types:
    count = CaseDocument.objects.filter(document_type=dt['document_type']).count()
    print(f"{dt['document_type']}: {count} documents")
