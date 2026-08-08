import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from cases.models import Case
from core.models import AuditLog


class Command(BaseCommand):
    help = (
        "Normalize urgency from rush to normal for legacy terminal cases "
        "(cancelled/declined) for an explicit, targeted case list."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-md",
            default="docs/LEGACY_RUSH_TERMINAL_CASES_PROD.md",
            help="Markdown file containing a table with case numbers in the first column.",
        )
        parser.add_argument(
            "--case-id",
            action="append",
            dest="case_ids",
            default=[],
            help="Case number to include (repeatable). If provided, adds to IDs parsed from --source-md.",
        )
        parser.add_argument(
            "--actor",
            default="",
            help="Username to attribute in AuditLog.user. Optional.",
        )
        parser.add_argument(
            "--reason",
            default=(
                "Legacy data fix: terminal case had stale rush urgency and was normalized to normal."
            ),
            help="Reason text stored in AuditLog metadata.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply updates. Without this flag, command runs in dry-run mode.",
        )

    def handle(self, *args, **options):
        source_md = options["source_md"]
        explicit_case_ids = options["case_ids"] or []
        actor_username = (options["actor"] or "").strip()
        reason = options["reason"]
        apply_changes = bool(options["apply"])

        case_ids = set(explicit_case_ids)
        if source_md:
            case_ids.update(self._parse_case_ids_from_md(source_md))

        if not case_ids:
            raise CommandError(
                "No case IDs were provided. Supply --case-id and/or a valid --source-md file."
            )

        actor_user = None
        if actor_username:
            actor_user = User.objects.filter(username=actor_username).first()
            if not actor_user:
                raise CommandError(f"Actor username not found: {actor_username}")

        selected_ids = sorted(case_ids)
        selected_qs = Case.objects.filter(external_case_id__in=selected_ids).select_related("member")
        selected_by_id = {c.external_case_id: c for c in selected_qs}

        missing_ids = [cid for cid in selected_ids if cid not in selected_by_id]

        eligible = []
        skipped_not_terminal_or_not_rush = []
        for cid in selected_ids:
            case = selected_by_id.get(cid)
            if not case:
                continue
            if case.status in ("cancelled", "declined") and case.urgency == "rush":
                eligible.append(case)
            else:
                skipped_not_terminal_or_not_rush.append(case)

        self.stdout.write(self.style.WARNING("Targeted legacy rush normalization"))
        self.stdout.write(f"Source markdown: {source_md}")
        self.stdout.write(f"Selected case IDs: {len(selected_ids)}")
        self.stdout.write(f"Found in database: {len(selected_by_id)}")
        self.stdout.write(f"Eligible for update: {len(eligible)}")
        self.stdout.write(f"Skipped (not terminal/rush): {len(skipped_not_terminal_or_not_rush)}")
        self.stdout.write(f"Missing IDs: {len(missing_ids)}")

        if missing_ids:
            self.stdout.write(self.style.WARNING("Missing case IDs:"))
            for cid in missing_ids:
                self.stdout.write(f"  - {cid}")

        if skipped_not_terminal_or_not_rush:
            self.stdout.write(self.style.WARNING("Skipped cases:"))
            for case in skipped_not_terminal_or_not_rush:
                self.stdout.write(
                    f"  - {case.external_case_id}: status={case.status}, urgency={case.urgency}"
                )

        if not eligible:
            self.stdout.write(self.style.SUCCESS("No eligible cases to update."))
            return

        self.stdout.write("Eligible cases:")
        for case in eligible:
            advisor = "(none)"
            if case.member:
                advisor = case.member.get_full_name() or case.member.username
            employee = f"{case.employee_first_name} {case.employee_last_name}".strip()
            self.stdout.write(
                f"  - {case.external_case_id} | {employee} | advisor={advisor} | "
                f"status={case.status} | urgency={case.urgency}"
            )

        if not apply_changes:
            self.stdout.write(
                self.style.WARNING(
                    "DRY-RUN ONLY. Re-run with --apply to persist changes and write audit logs."
                )
            )
            return

        with transaction.atomic():
            for case in eligible:
                old_urgency = case.urgency
                case.urgency = "normal"
                case.save(update_fields=["urgency"])

                AuditLog.log_activity(
                    user=actor_user,
                    action_type="case_rush_downgraded",
                    description=(
                        "Legacy data fix applied: urgency normalized from rush to normal "
                        f"for terminal case {case.external_case_id}."
                    ),
                    case=case,
                    changes={
                        "urgency": {
                            "before": old_urgency,
                            "after": "normal",
                        }
                    },
                    metadata={
                        "source": "management_command",
                        "command": "fix_legacy_terminal_rush",
                        "source_md": source_md,
                        "reason": reason,
                        "target_statuses": ["cancelled", "declined"],
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Applied update to {len(eligible)} case(s) and wrote {len(eligible)} audit log entries."
            )
        )

    def _parse_case_ids_from_md(self, md_path):
        path = Path(md_path)
        if not path.exists():
            raise CommandError(f"Markdown source file not found: {md_path}")

        content = path.read_text(encoding="utf-8", errors="ignore")
        case_ids = set()

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line.startswith("|"):
                continue
            if "Case Number" in line or line.startswith("|---"):
                continue

            # First markdown table cell is case number.
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not cells:
                continue

            first_cell = cells[0]
            if re.match(r"^[A-Za-z0-9-]+$", first_cell):
                case_ids.add(first_cell)

        return case_ids
