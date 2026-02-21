#!/usr/bin/env python
"""
Verify the most recent case and its documents
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case, CaseDocument

# Get the most recent case
latest_case = Case.objects.order_by('-created_at').first()

if not latest_case:
    print("\n❌ No cases found in database")
else:
    print("\n=== LATEST CASE ===\n")
    print(f"Case ID (External): {latest_case.external_case_id}")
    print(f"Case ID (Internal): {latest_case.id}")
    print(f"Status: {latest_case.status}")
    print(f"Member: {latest_case.member.username if latest_case.member else 'None'}")
    print(f"Employee: {latest_case.employee_first_name} {latest_case.employee_last_name}")
    print(f"Workshop Code: {latest_case.workshop_code}")
    print(f"Urgency: {latest_case.urgency}")
    print(f"Due Date: {latest_case.date_due}")
    print(f"Created: {latest_case.created_at}")
    
    # Get documents for this case
    documents = CaseDocument.objects.filter(case=latest_case).order_by('document_type', '-uploaded_at')
    
    print(f"\n=== DOCUMENTS ({documents.count()}) ===\n")
    
    if documents.count() == 0:
        print("❌ No documents found")
    else:
        fact_finder_count = 0
        supporting_count = 0
        
        for doc in documents:
            print(f"Type: {doc.document_type}")
            print(f"  Filename: {doc.original_filename}")
            print(f"  Size: {doc.file_size / 1024:.2f} KB")
            print(f"  Uploaded: {doc.uploaded_at}")
            print(f"  Path: {doc.file.name}")
            print()
            
            if doc.document_type == 'fact_finder':
                fact_finder_count += 1
            elif doc.document_type == 'supporting':
                supporting_count += 1
        
        print(f"SUMMARY: {fact_finder_count} Federal Fact Finder, {supporting_count} Supporting documents")
        
        if fact_finder_count == 1 and supporting_count == 2:
            print("\n✅ ALL DOCUMENTS VERIFIED - Ready to submit!")
        else:
            print(f"\n⚠️ Document count mismatch. Expected 1 FF + 2 Supporting, got {fact_finder_count} + {supporting_count}")
