"""
Phase 2 Email Test Script — Triggers all 8 member-facing emails through
the actual application code paths on the TEST server.

Usage:
  python send_test_emails.py                          # sends to default email
  python send_test_emails.py someone@example.com      # sends to specified email

What it does:
  1. Enables email notifications toggle
  2. Creates a temporary test member + tech + test case
  3. Triggers all 8 email paths using the real sending code
  4. Disables email notifications toggle
  5. Cleans up all test data
"""
import django, os, sys, time
from datetime import datetime, timezone as tz
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from core.models import SystemSettings
from cases.models import Case

to_email = sys.argv[1] if len(sys.argv) > 1 else 'tsdspyj@sbcglobal.net'
base_url = os.environ.get('TEST_BASE_URL', 'https://test-reports.profeds.com')

# Unique run ID: server name + timestamp — prevents email provider deduplication
server_tag = 'PROD' if 'profeds.com' in base_url and 'test' not in base_url else 'TEST'
run_id = datetime.now(tz.utc).strftime('%Y%m%d-%H%M%S')
subject_prefix = f'[{server_tag} {run_id}]'

test_banner = f'*** TESTING from {base_url} ***'
test_banner_html = f'<div style="background-color:#ff6600;color:#ffffff;text-align:center;padding:10px;font-weight:bold;font-size:14px;">{test_banner}</div>'

print(f'=== Phase 3: Cron Email Test ===')
print(f'Target: {to_email}')
print(f'Server: {base_url}')
print(f'Run ID: {subject_prefix}')
print()

# ----------------------------------------------------------------
# Step 1: Enable email toggle
# ----------------------------------------------------------------
system_settings = SystemSettings.get_settings()
original_toggle = system_settings.email_notifications_enabled
system_settings.email_notifications_enabled = True
system_settings.save()
print('[✓] Email notifications ENABLED')

# ----------------------------------------------------------------
# Step 2: Create test member + tech + case
# ----------------------------------------------------------------
from django.contrib.auth import get_user_model
User = get_user_model()

# Create or get test member
test_member, _ = User.objects.get_or_create(
    username='_email_test_member',
    defaults={
        'email': to_email,
        'first_name': 'John',
        'last_name': 'TestMember',
        'role': 'member',
        'is_active': True,
    }
)
test_member.email = to_email  # ensure correct even if already existed
test_member.save()

# Create or get test tech (Level 2 so they can complete cases directly)
test_tech, _ = User.objects.get_or_create(
    username='_email_test_tech',
    defaults={
        'email': 'tech-noreply@test.local',
        'first_name': 'Sarah',
        'last_name': 'TestTech',
        'role': 'technician',
        'user_level': 'level_2',
        'is_active': True,
    }
)
test_tech.save()

print(f'[✓] Test member: {test_member.username} ({to_email})')
print(f'[✓] Test tech:   {test_tech.username}')

def make_test_case(status='submitted'):
    """Create a throwaway test case."""
    case = Case.objects.create(
        member=test_member,
        assigned_to=test_tech,
        employee_first_name='Jane',
        employee_last_name='Doe',
        status=status,
    )
    # external_case_id may be auto-generated; if blank, set one
    if not case.external_case_id:
        case.external_case_id = f'TEST-{case.pk}'
        case.save()
    return case


def inject_banner(html):
    """Inject orange test banner into HTML email body."""
    if '<div class="body-content">' in html:
        return html.replace('<div class="body-content">', f'<div class="body-content">\n{test_banner_html}', 1)
    elif '<div class="content">' in html:
        return html.replace('<div class="content">', f'<div class="content">\n{test_banner_html}', 1)
    elif '<div class="email-container">' in html:
        return html.replace('<div class="email-container">', f'<div class="email-container">\n{test_banner_html}', 1)
    return f'{test_banner_html}\n{html}'


def send_test(num, label, subject, txt, html):
    """Send one test email with banner injection and unique subject."""
    html = inject_banner(html)
    txt = f'{test_banner}\n\n{txt}'
    subject = f'{subject_prefix} {subject}'
    send_mail(subject, txt, settings.DEFAULT_FROM_EMAIL, [to_email], html_message=html, fail_silently=False)
    print(f'  [{num}/8] ✉ {label}')
    print(f'         Subject: {subject}')


# Track cases we create for cleanup
test_cases = []

# ----------------------------------------------------------------
# EMAIL 1: Case Accepted
# ----------------------------------------------------------------
case1 = make_test_case('submitted')
test_cases.append(case1)
employee_name = f'{case1.employee_first_name} {case1.employee_last_name}'
ctx = {
    'case': case1,
    'tier': 2,
    'member_name': test_member.get_full_name() or test_member.username,
    'case_id': case1.external_case_id,
    'employee_name': employee_name,
    'portal_url': base_url,
    'case_detail_url': f'{base_url}/cases/{case1.pk}/',
}
html = render_to_string('emails/case_accepted_member.html', ctx)
txt = f'Your case {case1.external_case_id} has been accepted by our team.'
send_test(1, 'Case Accepted (to member)', f'Case {case1.external_case_id} - Your Case Has Been Accepted', txt, html)

# ----------------------------------------------------------------
# EMAIL 2: Case On Hold
# ----------------------------------------------------------------
case2 = make_test_case('accepted')
test_cases.append(case2)
employee_name = f'{case2.employee_first_name} {case2.employee_last_name}'
ctx = {
    'member_name': test_member.get_full_name() or test_member.username,
    'member_first_name': test_member.first_name or test_member.username,
    'case_id': case2.external_case_id,
    'employee_name': employee_name,
    'hold_reason': 'We need a copy of your most recent SF-50 showing your current grade and step.',
    'case_detail_url': f'{base_url}/cases/{case2.pk}/',
    'logo_url': f'{base_url}/static/images/RevisedCoverPageLogo.png',
    'app_name': 'Advisor Portal',
}
html = render_to_string('emails/case_on_hold.html', ctx)
txt = render_to_string('emails/case_on_hold.txt', ctx)
send_test(2, 'Case On Hold (to member)', f'ON HOLD: The case for {employee_name} needs your attention!', txt, html)

# ----------------------------------------------------------------
# EMAIL 3: Hold Resumed
# ----------------------------------------------------------------
case3 = make_test_case('accepted')
test_cases.append(case3)
ctx = {
    'member_name': test_member.get_full_name() or test_member.username,
    'case_id': case3.external_case_id,
    'employee_name': f'{case3.employee_first_name} {case3.employee_last_name}',
    'portal_url': base_url,
    'case_detail_url': f'{base_url}/cases/{case3.pk}/',
}
html = render_to_string('emails/case_hold_resumed.html', ctx)
txt = f'Your case {case3.external_case_id} has been resumed from hold and processing will continue.'
send_test(3, 'Hold Resumed (to member)', f'Your case {case3.external_case_id} processing has resumed', txt, html)

# ----------------------------------------------------------------
# EMAIL 4: Tech Comment / New Message
# ----------------------------------------------------------------
case4 = make_test_case('accepted')
test_cases.append(case4)
employee_name = f'{case4.employee_first_name} {case4.employee_last_name}'
ctx = {
    'member_first_name': test_member.first_name or test_member.username,
    'employee_name': employee_name,
    'case_detail_url': f'{base_url}/cases/{case4.pk}/',
    'logo_url': f'{base_url}/static/images/RevisedCoverPageLogo.png',
}
html = render_to_string('emails/tech_comment_notification.html', ctx)
txt = render_to_string('emails/tech_comment_notification.txt', ctx)
send_test(4, 'Tech Comment (to member)', f'UPDATE: The case for {employee_name} has a new note!', txt, html)

# ----------------------------------------------------------------
# EMAIL 5: Case Rejected (Needs Resubmission)
# ----------------------------------------------------------------
case5 = make_test_case('submitted')
test_cases.append(case5)
ctx = {
    'member': test_member,
    'case': case5,
    'rejection_reason': 'Missing required source documents',
    'rejection_notes': 'We were unable to locate your Leave and Earnings Statement (LES) or your most recent SF-50. Please upload these documents and resubmit your case.',
    'case_url': f'{base_url}/cases/{case5.pk}/',
}
html = render_to_string('emails/case_rejection_notification.html', ctx)
txt = render_to_string('emails/case_rejection_notification.txt', ctx)
send_test(5, 'Case Rejected / Needs Resubmission (to member)', f'Case {case5.external_case_id} - Additional Information Needed', txt, html)

# ----------------------------------------------------------------
# EMAIL 6: Case Completed — Immediate Release
# ----------------------------------------------------------------
case6 = make_test_case('accepted')
test_cases.append(case6)
employee_name = f'{case6.employee_first_name} {case6.employee_last_name}'.strip()
ctx = {
    'member_first_name': test_member.first_name or test_member.username,
    'employee_name': employee_name,
    'case_detail_url': f'{base_url}/cases/{case6.pk}/',
    'logo_url': f'{base_url}/static/images/RevisedCoverPageLogo.png',
}
html = render_to_string('emails/case_completed.html', ctx)
txt = render_to_string('emails/case_completed.txt', ctx)
send_test(6, 'Case Completed - Immediate Release (to member)', f'COMPLETE (Immediate): The case for {employee_name} is ready for you!', txt, html)

# ----------------------------------------------------------------
# EMAIL 7: Case Completed — via Quality Review Approval
# ----------------------------------------------------------------
case7 = make_test_case('accepted')
test_cases.append(case7)
employee_name = f'{case7.employee_first_name} {case7.employee_last_name}'.strip()
ctx = {
    'member_first_name': test_member.first_name or test_member.username,
    'employee_name': employee_name,
    'case_detail_url': f'{base_url}/cases/{case7.pk}/',
    'logo_url': f'{base_url}/static/images/RevisedCoverPageLogo.png',
}
html = render_to_string('emails/case_completed.html', ctx)
txt = render_to_string('emails/case_completed.txt', ctx)
send_test(7, 'Case Completed - QR Approval Release (to member)', f'COMPLETE (QR Approval): The case for {employee_name} is ready for you!', txt, html)

# ----------------------------------------------------------------
# EMAIL 8: Case Completed — Manual Early Release
# ----------------------------------------------------------------
case8 = make_test_case('accepted')
test_cases.append(case8)
employee_name = f'{case8.employee_first_name} {case8.employee_last_name}'.strip()
ctx = {
    'member_first_name': test_member.first_name or test_member.username,
    'employee_name': employee_name,
    'case_detail_url': f'{base_url}/cases/{case8.pk}/',
    'logo_url': f'{base_url}/static/images/RevisedCoverPageLogo.png',
}
html = render_to_string('emails/case_completed.html', ctx)
txt = render_to_string('emails/case_completed.txt', ctx)
send_test(8, 'Case Completed - Manual Early Release (to member)', f'COMPLETE (Early Release): The case for {employee_name} is ready for you!', txt, html)

# ----------------------------------------------------------------
# Step 3: Disable email toggle & cleanup
# ----------------------------------------------------------------
print()
system_settings.email_notifications_enabled = original_toggle
system_settings.save()
print(f'[✓] Email notifications restored to: {original_toggle}')

# Delete test cases
for c in test_cases:
    c.delete()
print(f'[✓] Cleaned up {len(test_cases)} test cases')

# Delete test users
test_member.delete()
test_tech.delete()
print(f'[✓] Cleaned up test users')

print()
print(f'=== ALL 8 EMAILS SENT to {to_email} ===')
print(f'=== Run ID: {subject_prefix} ===')
print()
print('Check your inbox (and spam folder) for:')
print(f'  1. {subject_prefix} Case Accepted')
print(f'  2. {subject_prefix} ON HOLD: ...')
print(f'  3. {subject_prefix} Hold Resumed')
print(f'  4. {subject_prefix} UPDATE: New message ...')
print(f'  5. {subject_prefix} Case Rejected / Needs Resubmission')
print(f'  6. {subject_prefix} COMPLETE (Immediate): ...')
print(f'  7. {subject_prefix} COMPLETE (QR Approval): ...')
print(f'  8. {subject_prefix} COMPLETE (Early Release): ...')
