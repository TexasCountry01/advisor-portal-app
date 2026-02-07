#!/usr/bin/env python
"""
Database Inventory Script
Creates a comprehensive inventory of all cases and their associated artifacts
before performing cascade deletes. Useful for testing delete functionality.
"""
import os
import django
import json
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import (
    Case, CaseDocument, CaseReport, CaseNote, APICallLog,
    CaseReviewHistory, CreditAuditLog, CaseNotification,
    CaseChangeRequest, CaseMessage, UnreadMessage
)
from accounts.models import User, AuditLog
from django.db.models import Count

def get_case_inventory():
    """Get detailed inventory of all cases and their artifacts"""
    
    print("\n" + "="*80)
    print("DATABASE INVENTORY - BEFORE DELETION")
    print("="*80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Overall statistics
    total_cases = Case.objects.count()
    total_users = User.objects.count()
    total_employees = User.objects.filter(role='member').count()
    
    print(f"SUMMARY STATISTICS:")
    print(f"  Total Cases: {total_cases}")
    print(f"  Total Users: {total_users}")
    print(f"  Total Employees (Members): {total_employees}")
    print(f"  Total Documents: {CaseDocument.objects.count()}")
    print(f"  Total Reports: {CaseReport.objects.count()}")
    print(f"  Total Notes: {CaseNote.objects.count()}")
    print(f"  Total API Call Logs: {APICallLog.objects.count()}")
    print(f"  Total Case Review Histories: {CaseReviewHistory.objects.count()}")
    print(f"  Total Credit Audit Logs: {CreditAuditLog.objects.count()}")
    print(f"  Total Case Notifications: {CaseNotification.objects.count()}")
    print(f"  Total Case Change Requests: {CaseChangeRequest.objects.count()}")
    print(f"  Total Case Messages: {CaseMessage.objects.count()}")
    print(f"  Total Unread Messages: {UnreadMessage.objects.count()}")
    print(f"  Total Audit Logs: {AuditLog.objects.count()}\n")
    
    # Detailed case inventory
    inventory = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_cases': total_cases,
            'total_users': total_users,
            'total_employees': total_employees,
            'total_documents': CaseDocument.objects.count(),
            'total_reports': CaseReport.objects.count(),
            'total_notes': CaseNote.objects.count(),
            'total_api_call_logs': APICallLog.objects.count(),
            'total_case_review_histories': CaseReviewHistory.objects.count(),
            'total_credit_audit_logs': CreditAuditLog.objects.count(),
            'total_case_notifications': CaseNotification.objects.count(),
            'total_case_change_requests': CaseChangeRequest.objects.count(),
            'total_case_messages': CaseMessage.objects.count(),
            'total_unread_messages': UnreadMessage.objects.count(),
            'total_audit_logs': AuditLog.objects.count(),
        },
        'cases': []
    }
    
    # Detailed inventory for each case
    print("DETAILED CASE INVENTORY:")
    print("-" * 80)
    
    for case in Case.objects.all().order_by('id'):
        case_data = {
            'case_id': case.id,
            'external_case_id': case.external_case_id,
            'employee_name': f"{case.employee_first_name} {case.employee_last_name}",
            'status': case.status,
            'member': case.member.username if case.member else None,
            'assigned_to': case.assigned_to.username if case.assigned_to else None,
            'reviewed_by': case.reviewed_by.username if case.reviewed_by else None,
            'created_by': case.created_by.username if case.created_by else None,
            'artifacts': {
                'documents': CaseDocument.objects.filter(case=case).count(),
                'reports': CaseReport.objects.filter(case=case).count(),
                'notes': CaseNote.objects.filter(case=case).count(),
                'api_call_logs': APICallLog.objects.filter(case=case).count(),
                'review_histories': CaseReviewHistory.objects.filter(case=case).count(),
                'credit_audit_logs': CreditAuditLog.objects.filter(case=case).count(),
                'notifications': CaseNotification.objects.filter(case=case).count(),
                'change_requests': CaseChangeRequest.objects.filter(case=case).count(),
                'messages': CaseMessage.objects.filter(case=case).count(),
                'unread_messages': UnreadMessage.objects.filter(case=case).count(),
            }
        }
        
        # Count audit logs related to this case
        case_audit_logs = AuditLog.objects.filter(
            resource_id=case.id,
            resource_type='case'
        ).count()
        case_data['artifacts']['audit_logs'] = case_audit_logs
        
        inventory['cases'].append(case_data)
        
        # Print summary
        total_artifacts = sum(case_data['artifacts'].values())
        print(f"\nCase {case.id}: {case.external_case_id}")
        print(f"  Employee: {case_data['employee_name']}")
        print(f"  Status: {case.status}")
        print(f"  Member: {case_data['member']}")
        print(f"  Assigned To: {case_data['assigned_to']}")
        print(f"  Reviewed By: {case_data['reviewed_by']}")
        print(f"  Created By: {case_data['created_by']}")
        print(f"  Total Artifacts: {total_artifacts}")
        for artifact_type, count in case_data['artifacts'].items():
            if count > 0:
                print(f"    - {artifact_type}: {count}")
    
    # Print all employees
    print("\n" + "="*80)
    print("ALL EMPLOYEES (MEMBERS):")
    print("-" * 80)
    
    employees = User.objects.filter(role='member').order_by('id')
    for emp in employees:
        # Count cases where this user is member, assigned_to, reviewed_by, or created_by
        member_cases = Case.objects.filter(member=emp).count()
        assigned_cases = Case.objects.filter(assigned_to=emp).count()
        reviewed_cases = Case.objects.filter(reviewed_by=emp).count()
        created_cases = Case.objects.filter(created_by=emp).count()
        
        # Count audit logs
        audit_logs = AuditLog.objects.filter(user=emp).count()
        
        if member_cases > 0 or assigned_cases > 0 or reviewed_cases > 0 or created_cases > 0 or audit_logs > 0:
            print(f"\n{emp.username} (ID: {emp.id})")
            if member_cases > 0:
                print(f"  Cases as Member: {member_cases}")
            if assigned_cases > 0:
                print(f"  Cases Assigned To: {assigned_cases}")
            if reviewed_cases > 0:
                print(f"  Cases Reviewed By: {reviewed_cases}")
            if created_cases > 0:
                print(f"  Cases Created: {created_cases}")
            if audit_logs > 0:
                print(f"  Audit Log Entries: {audit_logs}")
    
    # Save inventory to JSON file
    json_filename = f"inventory_before_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_filename, 'w') as f:
        json.dump(inventory, f, indent=2, default=str)
    
    print(f"\n" + "="*80)
    print(f"Inventory saved to: {json_filename}")
    print("="*80 + "\n")
    
    return inventory, json_filename

if __name__ == '__main__':
    inventory, filename = get_case_inventory()
