#!/usr/bin/env python
"""
Fix old test case documents - convert 'supporting' type to 'fact_finder'
Run this once to fix existing cases before the document type merge
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import CaseDocument

# Find all documents with 'supporting' type and convert to 'fact_finder'
supporting_docs = CaseDocument.objects.filter(document_type='supporting')
count = supporting_docs.count()

if count > 0:
    print(f"Found {count} documents with 'supporting' type")
    print("Converting to 'fact_finder'...")
    
    supporting_docs.update(document_type='fact_finder')
    
    print(f"✓ Updated {count} documents successfully!")
    print()
    
    # Show summary
    ff_count = CaseDocument.objects.filter(document_type='fact_finder').count()
    supporting_count = CaseDocument.objects.filter(document_type='supporting').count()
    
    print(f"Current document types:")
    print(f"  - fact_finder: {ff_count}")
    print(f"  - supporting: {supporting_count}")
else:
    print("No documents with 'supporting' type found")
