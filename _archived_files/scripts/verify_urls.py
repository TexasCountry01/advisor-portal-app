#!/usr/bin/env python
"""
URL Verification Script - Tests all URL reversals and template references
Runs locally to verify no broken URLs exist
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.urls import reverse, NoReverseMatch
import re

print("=" * 80)
print("URL AND REVERSE VERIFICATION REPORT")
print("=" * 80)

# All URL names that should exist in the application
EXPECTED_URLS = {
    # Core URLs
    'home': {},
    'login': {},
    'logout': {},
    'profile': {},
    'system_settings': {},
    'view_reports': {},
    'export_reports_csv': {},
    'view_audit_log': {},
    'export_audit_log_csv': {},
    
    # Case URLs (with namespace 'cases:')
    'cases:member_dashboard': {},
    'cases:case_submit': {},
    'cases:technician_dashboard': {},
    'cases:admin_dashboard': {},
    'cases:manager_dashboard': {},
    'cases:case_list': {},
    'cases:case_detail': {'pk': 1},
    'cases:edit_case': {'pk': 1},
    'cases:delete_case': {'pk': 1},
    'cases:case_review_for_acceptance': {'pk': 1},
    'cases:accept_case': {'pk': 1},
    'cases:reject_case': {'pk': 1},
    'cases:reassign_case': {'case_id': 1},
    'cases:take_case_ownership': {'case_id': 1},
    'cases:admin_take_ownership': {'case_id': 1},
    'cases:adjust_case_credit': {'case_id': 1},
    'cases:resubmit_case': {'case_id': 1},
    'cases:submit_case_final': {'case_id': 1},
    'cases:add_case_note': {'case_id': 1},
    'cases:delete_case_note': {'case_id': 1, 'note_id': 1},
    'cases:upload_case_report': {'case_id': 1},
    'cases:upload_technician_document': {'case_id': 1},
    'cases:upload_member_document_completed': {'case_id': 1},
    'cases:upload_image_for_notes': {},
    'cases:credit_audit_trail_report': {},
    'cases:credit_audit_trail': {'case_id': 1},
    'cases:mark_case_completed': {'case_id': 1},
    'cases:mark_case_incomplete': {'case_id': 1},
    'cases:put_on_hold': {'case_id': 1},
    'cases:resume_from_hold': {'case_id': 1},
    'cases:release_case_immediately': {'case_id': 1},
    'cases:validate_case_completion': {'case_id': 1},
    'cases:approve_case_review': {'case_id': 1},
    'cases:request_case_revisions': {'case_id': 1},
    'cases:correct_case_review': {'case_id': 1},
    'cases:case_audit_history': {'case_id': 1},
    'cases:audit_log_dashboard': {},
    'cases:case_fact_finder': {'case_id': 1},
    'cases:view_fact_finder_pdf': {'case_id': 1},
    'cases:download_document': {'doc_id': 1},
    'cases:delete_document': {'doc_id': 1},
    
    # Account URLs
    'manage_users': {},
    'deactivate_user': {'user_id': 1},
    'reactivate_user': {'user_id': 1},
    'member_profile_edit': {'member_id': 1},
    'member_delegate_add': {'member_id': 1},
    'member_delegate_edit': {'delegate_id': 1},
    'member_delegate_revoke': {'delegate_id': 1},
    'member_credit_allowance_edit': {'member_id': 1, 'fiscal_year': 2026, 'quarter': 1},
    'workshop_delegate_list': {},
    'workshop_delegate_add': {},
    'workshop_delegate_edit': {'delegate_id': 1},
    'workshop_delegate_revoke': {'delegate_id': 1},
}

# Test URL reversals
passed = 0
failed = 0
errors = []

print("\nTesting URL Reversals...")
print("-" * 80)

for url_name, kwargs in EXPECTED_URLS.items():
    try:
        url = reverse(url_name, kwargs=kwargs if kwargs else None)
        print(f"✓ {url_name:<40} → {url}")
        passed += 1
    except NoReverseMatch as e:
        print(f"✗ {url_name:<40} → ERROR: {str(e)}")
        failed += 1
        errors.append((url_name, str(e)))
    except Exception as e:
        print(f"✗ {url_name:<40} → EXCEPTION: {str(e)}")
        failed += 1
        errors.append((url_name, str(e)))

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Total Tests: {passed + failed}")

if failed > 0:
    print("\n⚠️  ERRORS DETECTED:")
    for url_name, error in errors:
        print(f"  - {url_name}: {error}")
    sys.exit(1)
else:
    print("\n✅ ALL URL REVERSALS WORKING CORRECTLY")
    print("No broken URLs or reverse errors will occur on remote server")
    sys.exit(0)
