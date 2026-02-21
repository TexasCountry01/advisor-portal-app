#!/usr/bin/env python
"""
Document Count Verification Script
Tests document counting across different upload scenarios
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case, CaseDocument
from django.db.models import Count, Q

def analyze_document_counts():
    """Analyze document counts across all cases"""
    
    print("\n" + "="*80)
    print("DOCUMENT COUNT ANALYSIS - 01/11/2026")
    print("="*80 + "\n")
    
    # Overall statistics
    total_cases = Case.objects.count()
    total_documents = CaseDocument.objects.count()
    
    print(f"Total Cases: {total_cases}")
    print(f"Total Documents: {total_documents}\n")
    
    # Document type breakdown
    print("Document Type Breakdown:")
    print("-" * 80)
    doc_types = CaseDocument.objects.values('document_type').annotate(count=Count('id'))
    for item in doc_types:
        print(f"  {item['document_type']:15} : {item['count']:4} documents")
    
    print("\n")
    
    # Cases with documents
    cases_with_docs = Case.objects.annotate(
        doc_count=Count('documents')
    ).filter(doc_count__gt=0).order_by('-doc_count')
    
    print(f"Cases with Documents: {cases_with_docs.count()} / {total_cases}")
    print("-" * 80 + "\n")
    
    # Show cases and their document breakdown
    print("Case-by-Case Breakdown:")
    print("-" * 80)
    
    for case in cases_with_docs[:20]:  # Show top 20
        print(f"\nCase {case.external_case_id} (ID: {case.id})")
        print(f"  Status: {case.status}")
        print(f"  Member: {case.member}")
        print(f"  Submitted: {case.date_submitted if case.date_submitted else 'Not submitted'}")
        
        # Count by type
        ff_count = case.documents.filter(document_type='fact_finder').count()
        support_count = case.documents.filter(document_type='supporting').count()
        report_count = case.documents.filter(document_type='report').count()
        other_count = case.documents.filter(document_type='other').count()
        total = case.documents.count()
        
        print(f"  Documents Total: {total}")
        print(f"    - Fact Finder: {ff_count}")
        print(f"    - Supporting: {support_count}")
        print(f"    - Report: {report_count}")
        print(f"    - Other: {other_count}")
        
        # Show documents
        for doc in case.documents.all()[:5]:
            print(f"      • {doc.original_filename[:50]:50} ({doc.document_type:12}) - {doc.uploaded_by}")
        
        if case.documents.count() > 5:
            print(f"      ... and {case.documents.count() - 5} more")
    
    print("\n" + "="*80)
    print("POTENTIAL ISSUES")
    print("="*80 + "\n")
    
    # Find cases where document type doesn't match upload method
    print("1. Cases with 'report' type documents (may be from technician uploads):")
    print("-" * 80)
    cases_with_reports = Case.objects.filter(
        documents__document_type='report'
    ).distinct()
    
    if cases_with_reports.exists():
        for case in cases_with_reports[:5]:
            report_docs = case.documents.filter(document_type='report')
            print(f"\n  Case {case.external_case_id}:")
            for doc in report_docs:
                print(f"    • {doc.original_filename} (uploaded by: {doc.uploaded_by})")
    else:
        print("  ✓ No cases with 'report' type documents")
    
    print("\n")
    print("2. Cases with mixed document types (may indicate workflow issues):")
    print("-" * 80)
    
    mixed_cases = Case.objects.annotate(
        type_count=Count('documents__document_type', distinct=True)
    ).filter(type_count__gt=1)
    
    if mixed_cases.exists():
        for case in mixed_cases[:5]:
            print(f"\n  Case {case.external_case_id} has {mixed_cases.count()} different document types:")
            types_in_case = case.documents.values('document_type').annotate(count=Count('id'))
            for item in types_in_case:
                print(f"    • {item['document_type']}: {item['count']} documents")
    else:
        print("  ✓ All cases have consistent document types")
    
    print("\n")
    print("3. Cases with zero documents (may need investigation):")
    print("-" * 80)
    
    cases_without_docs = Case.objects.annotate(
        doc_count=Count('documents')
    ).filter(doc_count=0)
    
    if cases_without_docs.exists():
        print(f"\n  {cases_without_docs.count()} cases without documents:")
        for case in cases_without_docs[:10]:
            status_note = f" - Status: {case.status}"
            print(f"    • Case {case.external_case_id}{status_note}")
    else:
        print("  ✓ All cases have at least one document")
    
    print("\n" + "="*80)
    print("COUNTING METHOD VERIFICATION")
    print("="*80 + "\n")
    
    # Test counting methods
    test_case = cases_with_docs.first() if cases_with_docs.exists() else None
    
    if test_case:
        print(f"Testing with Case: {test_case.external_case_id}\n")
        
        # Method 1: Direct count
        count1 = test_case.documents.count()
        print(f"Method 1 - .count(): {count1}")
        
        # Method 2: Using filter
        count2 = test_case.documents.filter(pk__isnull=False).count()
        print(f"Method 2 - .filter().count(): {count2}")
        
        # Method 3: Using all()
        count3 = len(test_case.documents.all())
        print(f"Method 3 - len(.all()): {count3}")
        
        # Method 4: By type
        ff = test_case.documents.filter(document_type='fact_finder').count()
        sup = test_case.documents.filter(document_type='supporting').count()
        rep = test_case.documents.filter(document_type='report').count()
        oth = test_case.documents.filter(document_type='other').count()
        count4 = ff + sup + rep + oth
        
        print(f"\nMethod 4 - Sum by type: {count4}")
        print(f"  (FF: {ff} + Supporting: {sup} + Report: {rep} + Other: {oth})")
        
        # Verify consistency
        print(f"\n✓ All methods consistent: {count1 == count2 == count3 == count4}")
    else:
        print("No cases available for testing")
    
    print("\n" + "="*80 + "\n")

def test_upload_scenarios():
    """Test document counting in different scenarios"""
    
    print("="*80)
    print("TESTING UPLOAD SCENARIOS")
    print("="*80 + "\n")
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Find a member and their draft cases
    members = User.objects.filter(role='member')
    print(f"Total Members: {members.count()}\n")
    
    print("Members with Draft Cases:")
    print("-" * 80)
    
    for member in members[:5]:
        draft_cases = Case.objects.filter(member=member, status='draft')
        if draft_cases.exists():
            print(f"\nMember: {member.username}")
            for case in draft_cases:
                doc_count = case.documents.count()
                print(f"  • Case {case.external_case_id}: {doc_count} documents")

if __name__ == '__main__':
    analyze_document_counts()
    test_upload_scenarios()
    
    print("\nVerification Complete!")
