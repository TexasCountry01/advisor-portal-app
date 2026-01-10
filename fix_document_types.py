#!/usr/bin/env python
"""
Fix document types in the database - change 'Federal Fact Finder' to 'fact_finder'
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import CaseDocument

# Update all documents with the old document type
updated_count = CaseDocument.objects.filter(
    document_type='Federal Fact Finder'
).update(document_type='fact_finder')

print(f"Updated {updated_count} document(s) from 'Federal Fact Finder' to 'fact_finder'")
