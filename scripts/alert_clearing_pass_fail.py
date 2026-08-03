#!/usr/bin/env python3
"""
PASS/FAIL validation for staff alert behavior.

What this checks:
1) Technician/Admin/Manager tile count equals alerts quick-filter count.
2) Technician clearing behavior: simulate reading one unread alert in a DB transaction
   and verify alerts count decreases by 1. Transaction is rolled back.

Usage:
  python scripts/alert_clearing_pass_fail.py
  python scripts/alert_clearing_pass_fail.py --username some.tech
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass


def bootstrap_django() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def fmt_result(r: CheckResult) -> str:
    status = "PASS" if r.passed else "FAIL"
    return f"[{status}] {r.name}: {r.detail}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate staff alert parity and clearing behavior.")
    parser.add_argument(
        "--username",
        help="Optional technician username to validate a specific technician.",
    )
    args = parser.parse_args()

    bootstrap_django()

    from django.db import transaction
    from django.contrib.auth import get_user_model

    from cases.models import Case, UnreadMessage
    from cases.views import _apply_staff_quick_filter, _build_staff_quick_tiles

    User = get_user_model()
    inactive_statuses = ["completed", "cancelled", "declined", "draft"]

    results: list[CheckResult] = []

    # Pick technician(s)
    tech_qs = User.objects.filter(role="technician", is_active=True).order_by("id")
    if args.username:
        tech_qs = tech_qs.filter(username__iexact=args.username)

    techs = list(tech_qs)
    if not techs:
        results.append(CheckResult("Technician selection", False, "No active technician found for given filter"))
    else:
        for tech in techs:
            scope = Case.objects.exclude(status="draft").filter(assigned_to=tech)

            tile_alerts = _build_staff_quick_tiles(scope, tech).get("alerts", 0)
            filter_alerts = _apply_staff_quick_filter(scope, "alerts", tech).count()
            parity_ok = tile_alerts == filter_alerts
            results.append(
                CheckResult(
                    f"Technician parity ({tech.username})",
                    parity_ok,
                    f"tile={tile_alerts}, filter={filter_alerts}",
                )
            )

            # Clearing simulation candidate: alert case for this tech with personal unread
            # and no member-update flag (so unread is the trigger we can test deterministically).
            alert_cases = _apply_staff_quick_filter(scope, "alerts", tech)
            candidate = (
                alert_cases.filter(has_member_updates=False)
                .filter(
                    id__in=UnreadMessage.objects.filter(user=tech).values_list("case_id", flat=True)
                )
                .exclude(status__in=inactive_statuses)
                .order_by("id")
                .first()
            )

            if not candidate:
                results.append(
                    CheckResult(
                        f"Technician clearing simulation ({tech.username})",
                        True,
                        "SKIP: no candidate case with personal unread-only trigger",
                    )
                )
                continue

            with transaction.atomic():
                before = _apply_staff_quick_filter(scope, "alerts", tech).count()
                deleted, _ = UnreadMessage.objects.filter(case=candidate, user=tech).delete()
                after = _apply_staff_quick_filter(scope, "alerts", tech).count()

                # Roll back: non-destructive validation.
                transaction.set_rollback(True)

            clearing_ok = deleted > 0 and after == max(before - 1, 0)
            results.append(
                CheckResult(
                    f"Technician clearing simulation ({tech.username})",
                    clearing_ok,
                    f"candidate_case={candidate.id}, deleted_unreads={deleted}, before={before}, after={after}",
                )
            )

    # Admin parity (team-level)
    admin = User.objects.filter(role="administrator", is_active=True).order_by("id").first()
    if admin:
        admin_scope = Case.objects.exclude(status="draft")
        tile_alerts = _build_staff_quick_tiles(admin_scope, admin).get("alerts", 0)
        filter_alerts = _apply_staff_quick_filter(admin_scope, "alerts", admin).count()
        results.append(
            CheckResult(
                f"Admin parity ({admin.username})",
                tile_alerts == filter_alerts,
                f"tile={tile_alerts}, filter={filter_alerts}",
            )
        )
    else:
        results.append(CheckResult("Admin parity", False, "No active administrator found"))

    # Manager parity (team-level)
    manager = User.objects.filter(role="manager", is_active=True).order_by("id").first()
    if manager:
        manager_scope = Case.objects.exclude(status="draft")
        tile_alerts = _build_staff_quick_tiles(manager_scope, manager).get("alerts", 0)
        filter_alerts = _apply_staff_quick_filter(manager_scope, "alerts", manager).count()
        results.append(
            CheckResult(
                f"Manager parity ({manager.username})",
                tile_alerts == filter_alerts,
                f"tile={tile_alerts}, filter={filter_alerts}",
            )
        )
    else:
        results.append(CheckResult("Manager parity", False, "No active manager found"))

    print("Alert Validation Results")
    print("=" * 80)
    for r in results:
        print(fmt_result(r))

    failed = [r for r in results if not r.passed]
    print("=" * 80)
    if failed:
        print(f"OVERALL: FAIL ({len(failed)} check(s) failed)")
        return 1

    print("OVERALL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
