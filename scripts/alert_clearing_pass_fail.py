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
    python scripts/alert_clearing_pass_fail.py --mode case --username some.tech --case-id 123
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass


def bootstrap_django() -> None:
    # Ensure repo root is importable when running from scripts/.
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
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
        "--mode",
        choices=["auto", "case"],
        default="auto",
        help="auto=scan users and run best-effort checks; case=validate one explicit technician/case",
    )
    parser.add_argument(
        "--username",
        help="Optional technician username to validate a specific technician.",
    )
    parser.add_argument(
        "--case-id",
        type=int,
        help="Case ID for explicit case-mode clearing validation.",
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

    if args.mode == "case":
        if not args.username or not args.case_id:
            results.append(
                CheckResult(
                    "Case mode input",
                    False,
                    "--mode case requires both --username and --case-id",
                )
            )
        else:
            tech = User.objects.filter(role="technician", is_active=True, username__iexact=args.username).first()
            if not tech:
                results.append(CheckResult("Technician selection", False, f"No active technician: {args.username}"))
            else:
                scope = Case.objects.exclude(status="draft").filter(assigned_to=tech)
                tile_alerts = _build_staff_quick_tiles(scope, tech).get("alerts", 0)
                filter_alerts = _apply_staff_quick_filter(scope, "alerts", tech).count()
                results.append(
                    CheckResult(
                        f"Technician parity ({tech.username})",
                        tile_alerts == filter_alerts,
                        f"tile={tile_alerts}, filter={filter_alerts}",
                    )
                )

                case = Case.objects.filter(pk=args.case_id).first()
                if not case:
                    results.append(CheckResult("Case lookup", False, f"Case not found: {args.case_id}"))
                elif case.assigned_to_id != tech.id:
                    results.append(
                        CheckResult(
                            "Case ownership",
                            False,
                            f"Case {case.id} assigned_to={getattr(case.assigned_to, 'username', None)} not {tech.username}",
                        )
                    )
                elif case.status in inactive_statuses:
                    results.append(CheckResult("Case status", False, f"Case {case.id} has inactive status {case.status}"))
                elif case.has_member_updates:
                    results.append(
                        CheckResult(
                            "Case trigger type",
                            False,
                            f"Case {case.id} has has_member_updates=True; use a personal-unread-only case for clearing check",
                        )
                    )
                elif not UnreadMessage.objects.filter(case=case, user=tech).exists():
                    results.append(
                        CheckResult(
                            "Unread prerequisite",
                            False,
                            f"Case {case.id} has no unread message for {tech.username}",
                        )
                    )
                else:
                    with transaction.atomic():
                        before = _apply_staff_quick_filter(scope, "alerts", tech).count()
                        before_has_case = _apply_staff_quick_filter(scope, "alerts", tech).filter(pk=case.pk).exists()
                        deleted, _ = UnreadMessage.objects.filter(case=case, user=tech).delete()
                        after = _apply_staff_quick_filter(scope, "alerts", tech).count()
                        after_has_case = _apply_staff_quick_filter(scope, "alerts", tech).filter(pk=case.pk).exists()

                        # Roll back: non-destructive validation.
                        transaction.set_rollback(True)

                    clearing_ok = before_has_case and deleted > 0 and after == max(before - 1, 0) and not after_has_case
                    results.append(
                        CheckResult(
                            f"Case clearing simulation ({tech.username}, case={case.id})",
                            clearing_ok,
                            f"deleted_unreads={deleted}, before={before}, after={after}, before_has_case={before_has_case}, after_has_case={after_has_case}",
                        )
                    )
    else:
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
