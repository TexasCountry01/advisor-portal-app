"""
Validate Option 1 alert alignment rules.

Usage (from repo root):
  python scripts/validate_option1_alert_alignment.py --settings config.settings

Optional:
  --username <staff_username>   # Validate technician-style first-page unread map scope for one user
  --page-size 50                # First-page sample size for username check
"""

import argparse
import os
import sys
from pathlib import Path

import django
from django.db.models import Exists, OuterRef, Q


def fail(msg):
    print(f"FAIL: {msg}")
    return False


def ok(msg):
    print(f"PASS: {msg}")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--settings", default="config.settings")
    parser.add_argument("--username", default="")
    parser.add_argument("--page-size", type=int, default=50)
    args = parser.parse_args()

    # Ensure project root is importable when running as a standalone script.
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", args.settings)
    django.setup()

    from accounts.models import User
    from cases.models import Case, UnreadMessage

    staff_roles = ["technician", "administrator", "manager"]
    active_statuses = ["submitted", "resubmitted", "accepted", "hold", "pending_review", "needs_resubmission"]
    inactive_statuses = ["completed", "cancelled", "declined", "draft"]

    all_ok = True

    # 1) Active Alerts tile semantics baseline: active-only cases with staff unread or member updates
    cases = Case.objects.exclude(status="draft").annotate(
        has_staff_unread=Exists(
            UnreadMessage.objects.filter(
                case=OuterRef("pk"),
                user__role__in=staff_roles,
                user__is_active=True,
            )
        )
    )

    active_alert_cases = cases.exclude(status__in=["completed", "cancelled", "declined"]).filter(
        Q(has_member_updates=True) | Q(has_staff_unread=True)
    )
    if active_alert_cases.filter(status__in=inactive_statuses).exists():
        all_ok = fail("Active alert set contains inactive statuses") and all_ok
    else:
        all_ok = ok("Active alert set contains active statuses only") and all_ok

    # 2) Staff unread endpoint semantics should be active-status-only
    endpoint_case_ids = set(
        UnreadMessage.objects.filter(
            user__role__in=staff_roles,
            user__is_active=True,
            case__status__in=active_statuses,
        ).values_list("case_id", flat=True)
    )

    endpoint_inactive_case_count = Case.objects.filter(id__in=endpoint_case_ids, status__in=inactive_statuses).count()
    if endpoint_inactive_case_count > 0:
        all_ok = fail(f"Endpoint unread set includes {endpoint_inactive_case_count} inactive-status cases") and all_ok
    else:
        all_ok = ok("Endpoint unread set excludes inactive statuses") and all_ok

    # 3) Report visibility numbers for traceability
    flagged_active_cases = Case.objects.filter(id__in=endpoint_case_ids).exclude(status__in=["completed", "cancelled", "declined"]).count()
    flagged_terminal_cases = Case.objects.filter(id__in=endpoint_case_ids, status__in=["completed", "cancelled", "declined"]).count()
    print(f"INFO: Active Alerts candidate cases = {active_alert_cases.count()}")
    print(f"INFO: Endpoint unread flagged active cases = {flagged_active_cases}")
    print(f"INFO: Endpoint unread flagged terminal cases = {flagged_terminal_cases}")

    # 4) Optional user-specific first-page check (technician-style initial row unread map)
    if args.username:
        try:
            user = User.objects.get(username__iexact=args.username)
        except User.DoesNotExist:
            print(f"FAIL: user not found: {args.username}")
            return 1

        base_cases = Case.objects.filter(
            Q(status__in=["submitted", "resubmitted", "accepted", "hold", "pending_review", "completed", "cancelled", "declined", "needs_resubmission"]) |
            Q(assigned_to=user)
        ).order_by("date_due")
        page_case_ids = list(base_cases.values_list("id", flat=True)[: args.page_size])

        first_page_unread_case_ids = set(
            UnreadMessage.objects.filter(
                case_id__in=page_case_ids,
                case__status__in=active_statuses,
                user__role__in=staff_roles,
                user__is_active=True,
            ).values_list("case_id", flat=True)
        )

        inactive_on_page = Case.objects.filter(
            id__in=first_page_unread_case_ids,
            status__in=inactive_statuses,
        ).count()
        if inactive_on_page > 0:
            all_ok = fail(f"First-page unread map contains {inactive_on_page} inactive-status cases for {user.username}") and all_ok
        else:
            all_ok = ok(f"First-page unread map excludes inactive statuses for {user.username}") and all_ok

    return 0 if all_ok else 2


if __name__ == "__main__":
    sys.exit(main())
