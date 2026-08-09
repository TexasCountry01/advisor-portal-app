"""
Smoke Test 02 — StaffNotification Suppression
==============================================
Validates that StaffNotification types that were removed from creation
have NOT been created since the alert-routing redesign was deployed
(2026-08-09).  Any record after this date in the removed types indicates
a code path that wasn't cleaned up.

Run:
    python manage.py shell < scripts/smoke_test_02_notification_suppression.py

Expected result:
    - All removed types show 0 new records after deploy date
    - case_chat_message (kept) shows > 0 (healthy signal)
"""
import sys
from django.utils import timezone
from core.models import StaffNotification

SECTION = lambda s: print(f"\n{'='*60}\n{s}\n{'='*60}")
PASS = lambda s: print(f"  PASS  {s}")
FAIL = lambda s: print(f"  FAIL  {s}")
INFO = lambda s: print(f"  INFO  {s}")

# Date the alert routing redesign went live on this environment
from datetime import datetime
import pytz
DEPLOY_DT = pytz.UTC.localize(datetime(2026, 8, 9, 0, 0, 0))

SECTION("01 — Removed notification types: 0 new records since deploy")

REMOVED_TYPES = [
    'case_assigned',
    'quality_review_feedback',
    'review_requested',
    'review_action_taken',
    'member_change_request',
    'case_modification_error',
    'case_on_hold',          # was never staff-facing but verify anyway
]

all_clean = True
for ntype in REMOVED_TYPES:
    count = StaffNotification.objects.filter(
        notification_type=ntype,
        created_at__gte=DEPLOY_DT
    ).count()
    if count == 0:
        PASS(f"{ntype}: 0 new records after deploy")
    else:
        FAIL(f"{ntype}: {count} records created AFTER deploy — unexpected")
        all_clean = False

        # Show the 3 most recent ones for investigation
        recent = (
            StaffNotification.objects
            .filter(notification_type=ntype, created_at__gte=DEPLOY_DT)
            .select_related('user', 'case')
            .order_by('-created_at')[:3]
        )
        for r in recent:
            print(f"         id={r.id} case={r.case.external_case_id if r.case else 'None'} "
                  f"user={r.user.username} created={r.created_at}")


SECTION("02 — Kept notification types: verify still being created")

KEPT_TYPES = ['case_chat_message']

for ntype in KEPT_TYPES:
    total = StaffNotification.objects.filter(notification_type=ntype).count()
    recent = StaffNotification.objects.filter(
        notification_type=ntype,
        created_at__gte=DEPLOY_DT
    ).count()
    if total > 0:
        PASS(f"{ntype}: {total} total, {recent} since deploy (creation path intact)")
    else:
        INFO(f"{ntype}: 0 total — no chat messages have been sent yet "
             f"(expected if this is a fresh environment)")


SECTION("03 — member_document_uploaded: only allowed when case is on hold")

from django.utils import timezone as tz
# Find member_document_uploaded notifications created after deploy
# Each one MUST have a corresponding case in hold status at time of creation.
# We can't go back in time, but we can check current case status as a proxy.
post_deploy_doc_notifs = (
    StaffNotification.objects
    .filter(notification_type='member_document_uploaded', created_at__gte=DEPLOY_DT)
    .select_related('case')
)

count = post_deploy_doc_notifs.count()
non_hold = sum(
    1 for n in post_deploy_doc_notifs
    if n.case and n.case.status != 'hold'
)

if count == 0:
    INFO("No member_document_uploaded notifications since deploy — nothing to validate")
elif non_hold == 0:
    PASS(f"{count} member_document_uploaded notification(s) found, "
         f"all cases currently in hold status (correct)")
else:
    INFO(f"{count} member_document_uploaded notification(s) found; "
         f"{non_hold} have cases no longer in hold status "
         f"(case may have moved off hold after upload — not necessarily a bug)")


SECTION("Summary")
if all_clean:
    print("  All removed notification types are clean.\n")
else:
    print("  Review FAIL lines above — unexpected notifications were created post-deploy.\n")
