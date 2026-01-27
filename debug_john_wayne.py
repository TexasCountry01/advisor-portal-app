from cases.models import Case, UnreadMessage, CaseMessage
from accounts.models import User

# Find JOliver
joliver = User.objects.filter(username='JOliver').first()
if not joliver:
    print("JOliver not found")
    exit()

print(f"Found: {joliver.username}")

# Get cases
cases = Case.objects.filter(member=joliver)
print(f"Cases for JOliver: {cases.count()}")

# Find John Wayne case
john_wayne = None
for case in cases:
    if 'Wayne' in case.external_case_id or 'Wayne' in (case.employee_first_name or ''):
        john_wayne = case
        break

if not john_wayne:
    print("John Wayne case not found")
    # List all cases
    print("Cases for JOliver:")
    for c in cases:
        print(f"  {c.external_case_id} - {c.employee_first_name} {c.employee_last_name}")
    exit()

print(f"\nJohn Wayne case: {john_wayne.external_case_id}")
print(f"  Status: {john_wayne.status}")
print(f"  Assigned to: {john_wayne.assigned_to}")

# Check UnreadMessage
unread_count = UnreadMessage.objects.filter(case=john_wayne, user=joliver).count()
print(f"\nUnreadMessage for JOliver on this case: {unread_count}")

# Check CaseMessage
messages = CaseMessage.objects.filter(case=john_wayne)
print(f"\nTotal messages on this case: {messages.count()}")
for msg in messages.order_by('-created_at'):
    print(f"  {msg.author.username}: {msg.message[:50]}")
    # Check if this message has unread record for joliver
    unread_for_msg = UnreadMessage.objects.filter(message=msg, user=joliver)
    print(f"    Unread for JOliver: {unread_for_msg.count()}")
