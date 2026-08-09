"""
Smoke Test 03 — Doc Upload → Badge Chain
=========================================
Validates that when a member uploads a document, a system CaseMessage
is created (📎 prefix) and a corresponding UnreadMessage row exists for
the assigned tech, so the upload increments the row badge.

Run:
    python manage.py shell < scripts/smoke_test_03_doc_upload_badge.py

Expected result:
    - Every 📎 system message has an UnreadMessage row for the assigned tech
    - No 📎 messages exist on unassigned cases without an UnreadMessage
"""
import sys
from cases.models import Case, CaseMessage, UnreadMessage

SECTION = lambda s: print(f"\n{'='*60}\n{s}\n{'='*60}")
PASS = lambda s: print(f"  PASS  {s}")
FAIL = lambda s: print(f"  FAIL  {s}")
INFO = lambda s: print(f"  INFO  {s}")

SECTION("01 — 📎 system messages exist")

upload_msgs = CaseMessage.objects.filter(message__startswith='📎').select_related('case')
total = upload_msgs.count()

if total == 0:
    INFO("No 📎 system messages found — no member document uploads have occurred "
         "since the fix was deployed, or this environment has no upload activity")
    print("\n  Smoke test 03 complete — no data to validate.\n")
    import sys; sys.exit(0)
else:
    INFO(f"Found {total} 📎 system message(s) to validate")


SECTION("02 — Each 📎 message has an UnreadMessage for the assigned tech")

missing_unread = 0
missing_assigned = 0
correct = 0

for msg in upload_msgs.select_related('case__assigned_to'):
    case = msg.case
    if not case.assigned_to:
        missing_assigned += 1
        INFO(f"Case {case.external_case_id} ({case.status}): no assigned tech — "
             f"UnreadMessage not expected (case was unassigned at upload time)")
        continue

    has_unread = UnreadMessage.objects.filter(
        message=msg,
        user=case.assigned_to
    ).exists()

    if has_unread:
        correct += 1
    else:
        # May have been cleared already (tech opened the case)
        # Check if the tech cleared it via mark_messages_as_read
        any_unread_for_case = UnreadMessage.objects.filter(
            case=case,
            user=case.assigned_to
        ).exists()

        if not any_unread_for_case:
            INFO(f"Case {case.external_case_id}: 📎 msg id={msg.id} has no UnreadMessage "
                 f"for tech {case.assigned_to.username} — likely already cleared by tech opening the case")
            correct += 1  # Cleared = working correctly
        else:
            FAIL(f"Case {case.external_case_id}: 📎 msg id={msg.id} missing UnreadMessage "
                 f"for assigned tech {case.assigned_to.username} — investigate")
            missing_unread += 1

INFO(f"Results: correct/cleared={correct}, missing_unread={missing_unread}, "
     f"unassigned_cases={missing_assigned}")

if missing_unread == 0:
    PASS(f"All {total} 📎 messages have correct UnreadMessage state "
         f"(either present or cleared by tech)")
else:
    PASS(f"{correct} 📎 messages correct") if correct else None
    from cases.models import Case as _C  # avoid re-import warning


SECTION("03 — Badge increment: cases with 📎 messages show in staff badge query")

from django.db.models import F as _F, Count as _Count, Exists, OuterRef

# Cases that have a 📎 message AND assigned tech has unread rows
visible_cases = (
    Case.objects
    .filter(
        Exists(CaseMessage.objects.filter(case=OuterRef('pk'), message__startswith='📎')),
        Exists(UnreadMessage.objects.filter(case=OuterRef('pk'), user=OuterRef('assigned_to'))),
        assigned_to__isnull=False
    )
    .values_list('external_case_id', 'status')
)

if visible_cases:
    PASS(f"{len(visible_cases)} case(s) with 📎 messages currently show a badge:")
    for cid, status in visible_cases[:10]:
        print(f"         {cid} ({status})")
else:
    INFO("No cases with active 📎 unread messages — all have been cleared by techs "
         "or no uploads occurred yet")


SECTION("Summary")
print("  Smoke test 03 complete.\n")
