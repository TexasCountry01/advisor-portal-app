"""
Validation tests for `fact_finder_content/pdf_structure_map.py` (Phase 1, with
Phase 1 Reconciliation corrections applied after
`docs/PDF_CONTENT_EDITOR_PHASE1_LARAVEL_VERIFICATION.md` became available).

These tests verify the structure map's INTERNAL consistency and its
agreement with other already-committed, Advisor-Portal-local artifacts:
`fact_finder_content/wiring_status.py` (WIRED_BLOCK_KEYS) and the committed
`PDF_CONTENT_BLOCK_INVENTORY.csv`. Per `PDF_CONTENT_STRUCTURE_MAP_DESIGN.md`
Section 8.3, none of this can (or claims to) re-verify the map against
`report_pdf.blade.php` itself. For the `srs_ss` shared-paragraph keys and the
Pension/SBP/FEGLI calculated-table placements, the authoritative source is
instead `docs/PDF_CONTENT_EDITOR_PHASE1_LARAVEL_VERIFICATION.md` — a direct
reading of the real Blade/PHP source performed outside this repository —
which is treated here as ground truth wherever it conflicts with the
original CSV's less-precise numbering (see
`CSV_POSITION_SUPERSEDED_BY_LARAVEL_VERIFICATION` in the module).

Tests are split into two groups:

- `StructureMapPureDataTests` (`unittest.TestCase`, no Django DB at all) —
  pure-Python checks against the module's own data, `WIRED_BLOCK_KEYS`, and
  a direct read of the committed CSV file. Fully deterministic; does not
  touch any database, and is not affected by the developer's personal
  LOCAL `db.sqlite3` in any way.
- `StructureMapDjangoFixtureTests` (`django.test.TestCase`) — uses Django's
  normal isolated *test* database (created and destroyed by the test
  runner; distinct from the developer's real `db.sqlite3`) to confirm every
  mapped key's declared group matches a real `ContentBlock.group` via the
  ORM, using fixtures created in `setUp`, the same pattern already used in
  `fact_finder_content/tests.py`. No migrations are run against, and no
  writes occur against, the normal LOCAL application database.
"""

import csv
import re
import unittest
from pathlib import Path

from django.test import TestCase

from fact_finder_content import pdf_structure_map as sm
from fact_finder_content.models import ContentBlock, ContentBlockGroup
from fact_finder_content.wiring_status import WIRED_BLOCK_KEYS

INVENTORY_CSV_PATH = Path(__file__).resolve().parent.parent / "PDF_CONTENT_BLOCK_INVENTORY.csv"

EXPECTED_GROUP_KEYS = (
    "cover", "pension", "sbp", "srs_ss", "fegli",
    "fehb", "fltcip", "tsp", "irs_penalty", "checklist",
)


def _parse_order_positions(order_text):
    """Extract the leading integer from each '/'-separated segment of a
    'Verified PDF Order (within group)' CSV cell, e.g.:
      '7' -> [7]
      '1 of 5 (mutually exclusive - exactly one renders)' -> [1]
      '8 (FERS/Transfers branch) / 1 (CSRS/CSRS Offset branch - separate page)' -> [8, 1]
    Note 'FERS/Transfers' (no surrounding spaces around its slash) is never
    mistaken for the ' / ' (spaced) dual-position separator.
    """
    positions = []
    for segment in order_text.split(" / "):
        match = re.match(r"\s*(\d+)", segment)
        if match:
            positions.append(int(match.group(1)))
    return positions


def _load_inventory_csv():
    """Return {block_key: (group, [position, ...])} parsed from the
    committed Inventory CSV. Pure file read, no DB, fully deterministic."""
    rows = {}
    with open(INVENTORY_CSV_PATH, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            key = row["Block Key"].strip()
            group = row["Group"].strip()
            order_text = row["Verified PDF Order (within group)"].strip()
            rows[key] = (group, _parse_order_positions(order_text))
    return rows


class StructureMapPureDataTests(unittest.TestCase):
    """Pure-Python checks — no Django database involved at all."""

    # Requirement 1: all 10 governed groups represented exactly once.
    def test_all_10_groups_represented_exactly_once(self):
        keys = [section.group_key for section in sm.PDF_STRUCTURE_MAP]
        self.assertEqual(len(keys), 10)
        self.assertEqual(len(keys), len(set(keys)), "A group_key is repeated across ReportSections")
        self.assertEqual(set(keys), set(EXPECTED_GROUP_KEYS))
        self.assertEqual(tuple(keys), EXPECTED_GROUP_KEYS, "Group order must match the verified PDF section order")

    # Requirement 2: all 98 keys in WIRED_BLOCK_KEYS are represented.
    def test_all_wired_keys_represented(self):
        flattened = sm.flatten_governed_keys()
        self.assertEqual(len(WIRED_BLOCK_KEYS), 98)
        missing = set(WIRED_BLOCK_KEYS) - set(flattened)
        self.assertEqual(missing, set(), f"WIRED_BLOCK_KEYS not represented in the map: {sorted(missing)}")

    # Requirement 3: every mapped governed key belongs to the correct group.
    def test_every_key_belongs_to_its_declared_group(self):
        for section, entry in sm.governed_entries():
            prefix = entry.key.split(".")[0]
            self.assertEqual(
                prefix, section.group_key,
                f"{entry.key!r} is declared under group {section.group_key!r} but its key prefix is {prefix!r}",
            )

    # Requirement 4: no unexpected governed keys are introduced.
    def test_no_unexpected_governed_keys(self):
        flattened = sm.flatten_governed_keys()
        extra = set(flattened) - set(WIRED_BLOCK_KEYS)
        self.assertEqual(extra, set(), f"Map contains keys not in WIRED_BLOCK_KEYS: {sorted(extra)}")
        # Two-way equality: exactly 98 keys, exactly matching WIRED_BLOCK_KEYS.
        self.assertEqual(set(flattened), set(WIRED_BLOCK_KEYS))

    # Requirement 5: duplicate references are rejected unless explicitly
    # authorized as intentional occurrences.
    def test_repeated_occurrences_match_allowlist(self):
        self.assertEqual(sm.dual_position_keys(), sm.REPEATED_KEY_ALLOWLIST)
        self.assertEqual(
            sm.REPEATED_KEY_ALLOWLIST,
            {
                "srs_ss.ss_eligibility",
                "srs_ss.ss_earnings_test",
                "srs_ss.ss_cola",
                "srs_ss.wep_paragraph",
            },
        )

    def test_unauthorized_duplicate_key_across_sections_is_rejected(self):
        """Demonstrates the rejection mechanism itself: a hand-built fake
        pair of ReportSections reusing the same key (not an authorized
        dual-BranchPosition reuse, but a flat duplicate SlotEntry in a
        second section) must be caught by flatten_governed_keys()."""
        fake_sections = (
            sm.ReportSection(
                group_key="pension",
                section_label="Fake A",
                entries=(
                    sm.SlotEntry(
                        kind=sm.SlotKind.GOVERNED,
                        key="pension.day_of_month_to_retire",
                        positions=(sm.BranchPosition(sm.BRANCH_DEFAULT, 1),),
                    ),
                ),
            ),
            sm.ReportSection(
                group_key="pension",
                section_label="Fake B (accidental duplicate)",
                entries=(
                    sm.SlotEntry(
                        kind=sm.SlotKind.GOVERNED,
                        key="pension.day_of_month_to_retire",
                        positions=(sm.BranchPosition(sm.BRANCH_DEFAULT, 1),),
                    ),
                ),
            ),
        )
        with self.assertRaises(ValueError):
            sm.flatten_governed_keys(fake_sections)

    # Requirement 6: branch positions are valid and unambiguous.
    def test_branch_positions_are_valid_and_unambiguous(self):
        for _section, entry in sm.governed_entries():
            self.assertGreater(len(entry.positions), 0, f"{entry.key!r} has no BranchPosition at all")
            branches_seen = [bp.branch for bp in entry.positions]
            self.assertEqual(
                len(branches_seen), len(set(branches_seen)),
                f"{entry.key!r} declares the same branch more than once — ambiguous position",
            )
            for bp in entry.positions:
                self.assertIsInstance(bp.position, int)
                self.assertGreater(bp.position, 0)
                self.assertIn(
                    bp.branch,
                    (sm.BRANCH_DEFAULT, sm.BRANCH_FERS_TRANSFERS, sm.BRANCH_CSRS_CSRS_OFFSET, sm.BRANCH_SHARED),
                )

    def test_srs_ss_uses_branch_dimension_others_use_default_only(self):
        for section in sm.PDF_STRUCTURE_MAP:
            branches = {
                bp.branch
                for entry in section.entries if entry.kind is sm.SlotKind.GOVERNED
                for bp in entry.positions
            }
            if section.group_key == "srs_ss":
                self.assertEqual(
                    branches, {sm.BRANCH_FERS_TRANSFERS, sm.BRANCH_CSRS_CSRS_OFFSET, sm.BRANCH_SHARED}
                )
            else:
                self.assertEqual(branches, {sm.BRANCH_DEFAULT}, f"{section.group_key} unexpectedly uses branches")

    # Requirement 7: mutually exclusive variants have valid, documented membership.
    def test_variant_ties_have_documented_conditions(self):
        ties = sm.variant_tie_groups()
        self.assertEqual(len(ties), 9, "Expected 9 documented variant-tie slots")
        for slot, members in ties.items():
            self.assertGreaterEqual(len(members), 2)
            for member in members:
                self.assertTrue(
                    member.system_type or member.retirement_type or member.description,
                    f"Tied entry {member.key!r} in slot {slot} has no documented condition",
                )

    def test_known_variant_tie_membership_matches_audit(self):
        ties = sm.variant_tie_groups()
        expected = {
            ("pension", "default", 1): {"pension.system_type_heading_fers", "pension.system_type_heading_non_fers"},
            ("pension", "default", 12): {"pension.your_federal_pension_deferred", "pension.your_federal_pension_not_deferred"},
            ("sbp", "default", 8): {"sbp.deferred_intro", "sbp.fers_transfers_intro_not_deferred", "sbp.csrs_intro"},
            ("sbp", "default", 9): {"sbp.levels_fers_transfers", "sbp.levels_csrs"},
            ("srs_ss", "shared", 1): {"srs_ss.summary_deferred_note", "srs_ss.summary_earnings_test_note"},
            ("fegli", "default", 10): {"fegli.coverage_elected_intro_deferred", "fegli.coverage_elected_intro_not_deferred"},
            ("fehb", "default", 8): {"fehb.deferred_sentence", "fehb.projection_intro_not_deferred"},
            ("tsp", "default", 10): {"tsp.match_threshold_sentence", "tsp.agency_match_explanation", "tsp.no_agency_match_csrs"},
            ("irs_penalty", "default", 1): {
                "irs_penalty.eligible_at_59_5", "irs_penalty.special_provision_meets_rules",
                "irs_penalty.special_provision_not_meets_rules", "irs_penalty.regular_not_meets_age55",
                "irs_penalty.regular_meets_age55",
            },
        }
        actual = {slot: {m.key for m in members} for slot, members in ties.items()}
        self.assertEqual(actual, expected)

    # Requirement 8: computed placeholders have no editable content key.
    def test_computed_placeholders_have_no_content_key(self):
        placeholders = list(sm.computed_entries())
        self.assertEqual(
            len(placeholders), 12,
            "Expected 12 computed placeholders (11 original + 1 from splitting SBP's survivor-benefit "
            "placeholder into two distinct, branch-specific tables per the Laravel verification)",
        )
        for _section, entry in placeholders:
            self.assertIsNone(entry.key)
            self.assertEqual(entry.kind, sm.SlotKind.COMPUTED)

    # Requirement 9: computed placeholders have unique identifiers and valid
    # placement anchors, including variant-group anchors.
    def test_computed_placeholders_have_unique_ids_and_valid_anchors(self):
        ids = [entry.placeholder_id for _s, entry in sm.computed_entries()]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate placeholder_id values found")
        for placeholder_id in ids:
            self.assertTrue(placeholder_id.startswith("computed:"))
            # A real ContentBlock.key can never contain ':' — structurally distinguishable.
            self.assertNotIn(":", placeholder_id[len("computed:"):])

        for section, entry in sm.computed_entries():
            governed_keys_in_section = {
                e.key for e in section.entries if e.kind is sm.SlotKind.GOVERNED
            }
            # Exactly one of anchor_after / anchor_after_variant_group must be set (enforced by
            # SlotEntry.__post_init__ too; re-asserted here as an explicit, discoverable test).
            self.assertEqual(
                sum(x is not None for x in (entry.anchor_after, entry.anchor_after_variant_group)), 1,
                f"{entry.placeholder_id!r} must set exactly one of anchor_after / anchor_after_variant_group",
            )
            if entry.anchor_after is not None:
                self.assertIn(
                    entry.anchor_after, governed_keys_in_section,
                    f"{entry.placeholder_id!r} anchors to {entry.anchor_after!r}, not a governed key in its own section",
                )
            else:
                self.assertGreaterEqual(
                    len(entry.anchor_after_variant_group), 2,
                    f"{entry.placeholder_id!r}'s anchor_after_variant_group must name a real variant group (2+ keys)",
                )
                for key in entry.anchor_after_variant_group:
                    self.assertIn(
                        key, governed_keys_in_section,
                        f"{entry.placeholder_id!r} anchors to variant-group member {key!r}, "
                        "not a governed key in its own section",
                    )

    def test_pension_and_fegli_calculated_tables_anchor_to_variant_group_not_one_variant(self):
        """The Pension and FEGLI deferred/not-deferred calculated tables must
        each be ONE placeholder anchored to BOTH variants as a unit — not
        duplicated per variant, and not anchored to only one variant (which
        would incorrectly imply the table is absent/different for the other
        case — Laravel Verification Sections 4 and 6)."""
        by_id = {entry.placeholder_id: entry for _s, entry in sm.computed_entries()}

        pension_table = by_id["computed:pension.multi_scenario_pension_projection_table"]
        self.assertIsNone(pension_table.anchor_after)
        self.assertEqual(
            set(pension_table.anchor_after_variant_group),
            {"pension.your_federal_pension_deferred", "pension.your_federal_pension_not_deferred"},
        )

        fegli_table = by_id["computed:fegli.current_coverage_table"]
        self.assertIsNone(fegli_table.anchor_after)
        self.assertEqual(
            set(fegli_table.anchor_after_variant_group),
            {"fegli.coverage_elected_intro_deferred", "fegli.coverage_elected_intro_not_deferred"},
        )

        # Exactly one placeholder each — not duplicated per narrative variant.
        pension_placeholder_ids = [pid for pid in by_id if pid.startswith("computed:pension.multi_scenario")]
        fegli_placeholder_ids = [pid for pid in by_id if pid.startswith("computed:fegli.current_coverage")]
        self.assertEqual(len(pension_placeholder_ids), 1)
        self.assertEqual(len(fegli_placeholder_ids), 1)

    def test_sbp_calculated_tables_are_two_distinct_mutually_exclusive_placeholders(self):
        """SBP's survivor-benefit projection tables are two physically
        distinct, mutually exclusive calculated tables (55%/partial for
        FERS/Transfers; 50%/25% for CSRS/CSRS Offset) — Laravel Verification
        Section 5. Must be two separately identifiable placeholders, each
        anchored to its own governed `sbp.levels_*` key and its own
        system_type branch, never presented as one shared/reused table."""
        by_id = {entry.placeholder_id: entry for _s, entry in sm.computed_entries()}

        fers_transfers_table = by_id["computed:sbp.survivor_benefit_projection_table_fers_transfers"]
        csrs_table = by_id["computed:sbp.survivor_benefit_projection_table_csrs"]

        self.assertNotEqual(fers_transfers_table.placeholder_id, csrs_table.placeholder_id)
        self.assertEqual(fers_transfers_table.anchor_after, "sbp.levels_fers_transfers")
        self.assertEqual(csrs_table.anchor_after, "sbp.levels_csrs")
        self.assertEqual(fers_transfers_table.system_type, ("FERS", "Transfers"))
        self.assertEqual(csrs_table.system_type, ("CSRS", "CSRS Offset"))
        # Mutually exclusive: no overlap between the two tables' applicable system types.
        self.assertEqual(set(fers_transfers_table.system_type) & set(csrs_table.system_type), set())
        # The old, single, unsplit placeholder_id must no longer exist.
        self.assertNotIn("computed:sbp.survivor_benefit_projection_table", by_id)

    def test_placeholder_id_can_never_collide_with_a_content_block_key(self):
        flattened = sm.flatten_governed_keys()
        placeholder_ids = {entry.placeholder_id for _s, entry in sm.computed_entries()}
        self.assertEqual(placeholder_ids & set(flattened), set())

    # Requirement 10: ungoverned sections cannot be treated as editable content.
    def test_ungoverned_sections_have_no_editable_key(self):
        self.assertEqual(len(sm.UNGOVERNED_SECTIONS), 2)
        for section in sm.UNGOVERNED_SECTIONS:
            self.assertIsInstance(section, sm.UngovernedSection)
            self.assertFalse(hasattr(section, "key"))
            self.assertTrue(section.label)
            # Must not collide with any real governed or computed identifier.
            self.assertNotIn(section.label, sm.flatten_governed_keys())

    def test_ungoverned_section_labels_match_task_requirements(self):
        labels = {section.label for section in sm.UNGOVERNED_SECTIONS}
        self.assertEqual(labels, {"Disclaimer & Release", "Data Used in Preparation of This Report"})
        for section in sm.UNGOVERNED_SECTIONS:
            self.assertEqual(section.after_group, "cover")
            self.assertEqual(section.before_group, "pension")

    # Requirement 11: unwired keys are excluded from the governed report sequence.
    def test_unwired_keys_excluded_from_governed_sequence(self):
        flattened = sm.flatten_governed_keys()
        unwired = sm.all_unwired_keys()
        self.assertEqual(unwired, {"checklist.next_steps", "fltcip.coverage_description"})
        self.assertEqual(unwired & set(flattened), set(), "An unwired key must not also be a GOVERNED entry")
        self.assertEqual(unwired & set(WIRED_BLOCK_KEYS), set(), "Unwired keys must not be in WIRED_BLOCK_KEYS")
        # Each unwired key is attached to its real group section, not floating free.
        unwired_by_group = sm.unwired_keys_by_group()
        self.assertEqual(unwired_by_group.get("checklist"), ("checklist.next_steps",))
        self.assertEqual(unwired_by_group.get("fltcip"), ("fltcip.coverage_description",))

    # Requirement 12: inactive keys are not presented as active PDF content.
    def test_inactive_keys_not_presented_as_active_content(self):
        self.assertEqual(sm.INACTIVE_BLOCK_KEYS, {"fegli.basic_description"})
        flattened = sm.flatten_governed_keys()
        self.assertEqual(sm.INACTIVE_BLOCK_KEYS & set(flattened), set())
        self.assertEqual(sm.INACTIVE_BLOCK_KEYS & sm.all_unwired_keys(), set())
        self.assertEqual(sm.INACTIVE_BLOCK_KEYS & set(WIRED_BLOCK_KEYS), set())

    # Requirement 13: the structure map agrees with the verified PDF
    # inventory wherever that inventory provides unambiguous ordering evidence.
    #
    # EXCEPTION: four srs_ss keys (CSV_POSITION_SUPERSEDED_BY_LARAVEL_VERIFICATION)
    # are intentionally excluded from the strict position-number comparison.
    # The Laravel verification report is stronger, more direct evidence (a
    # fresh, direct reading of the real Blade source) that supersedes the
    # original CSV's position numbers for exactly these four keys, whose CSV
    # numbering conflated a per-branch count with a separate shared-paragraph
    # count (see the module's "Phase 1 Reconciliation" docstring section and
    # the `srs_ss` ReportSection's inline comments). Their group assignment
    # and continued presence are still checked for all 98 keys, including
    # these four.
    def test_matches_inventory_csv_group_and_position(self):
        self.assertTrue(INVENTORY_CSV_PATH.exists(), f"Inventory CSV not found at {INVENTORY_CSV_PATH}")
        inventory = _load_inventory_csv()
        self.assertEqual(len(inventory), 98)

        flattened = sm.flatten_governed_keys()
        self.assertEqual(set(inventory), set(flattened), "CSV keys and map keys must match 1:1")

        for key, (csv_group, csv_positions) in inventory.items():
            section, entry = flattened[key]
            self.assertEqual(
                section.group_key, csv_group,
                f"{key!r}: map group {section.group_key!r} != CSV group {csv_group!r}",
            )
            if key in sm.CSV_POSITION_SUPERSEDED_BY_LARAVEL_VERIFICATION:
                continue
            map_positions = sorted(bp.position for bp in entry.positions)
            self.assertEqual(
                map_positions, sorted(csv_positions),
                f"{key!r}: map positions {map_positions} != CSV-parsed positions {sorted(csv_positions)}",
            )

    def test_csv_superseded_allowlist_is_exactly_the_four_shared_srs_ss_keys(self):
        self.assertEqual(
            sm.CSV_POSITION_SUPERSEDED_BY_LARAVEL_VERIFICATION,
            {
                "srs_ss.summary_deferred_note",
                "srs_ss.summary_earnings_test_note",
                "srs_ss.summary_ss_note",
                "srs_ss.wep_sentence",
            },
        )
        # All four must in fact use BRANCH_SHARED in the real map (otherwise this
        # allowlist would be stale documentation, not a live fact about the data).
        flattened = sm.flatten_governed_keys()
        for key in sm.CSV_POSITION_SUPERSEDED_BY_LARAVEL_VERIFICATION:
            _section, entry = flattened[key]
            self.assertTrue(
                all(bp.branch == sm.BRANCH_SHARED for bp in entry.positions),
                f"{key!r} is in the CSV-superseded allowlist but is not modeled entirely in BRANCH_SHARED",
            )

    def test_csv_order_parser_handles_known_formats(self):
        self.assertEqual(_parse_order_positions("7"), [7])
        self.assertEqual(_parse_order_positions("1 of 5 (mutually exclusive - exactly one renders)"), [1])
        self.assertEqual(
            _parse_order_positions("8 (FERS/Transfers branch) / 1 (CSRS/CSRS Offset branch - separate page)"),
            [8, 1],
        )
        self.assertEqual(_parse_order_positions("9 / 2"), [9, 2])
        self.assertEqual(_parse_order_positions("12 (FERS/Transfers + Deferred only)"), [12])

    # The module must not be importable as anything but self-consistent —
    # this re-runs the same internal checks performed at import time,
    # pinned here as an explicit, discoverable test rather than only a
    # side effect of importing the module.
    def test_module_self_validation_passes(self):
        sm._validate()  # must not raise


class SrsSsReconciliationTests(unittest.TestCase):
    """Tests added for the Phase 1 Reconciliation against
    `docs/PDF_CONTENT_EDITOR_PHASE1_LARAVEL_VERIFICATION.md`. Pure-Python,
    no Django database."""

    def test_shared_srs_ss_content_is_a_single_source_occurrence(self):
        """summary_deferred_note, summary_earnings_test_note, summary_ss_note,
        and wep_sentence must each have exactly ONE BranchPosition (a single
        real source occurrence), all in BRANCH_SHARED — not duplicated as
        separate branch-specific source occurrences. (summary_ss_note in
        particular: Laravel Verification Section 1 finding 1 / Section 3
        confirms it renders exactly once, not once per branch.)"""
        flattened = sm.flatten_governed_keys()
        shared_only_keys = (
            "srs_ss.summary_deferred_note",
            "srs_ss.summary_earnings_test_note",
            "srs_ss.summary_ss_note",
            "srs_ss.wep_sentence",
        )
        for key in shared_only_keys:
            _section, entry = flattened[key]
            self.assertEqual(len(entry.positions), 1, f"{key!r} must have exactly one source occurrence")
            self.assertEqual(entry.positions[0].branch, sm.BRANCH_SHARED, f"{key!r} must be in BRANCH_SHARED")
        # None of these four keys are in the dual-position allowlist — they are
        # genuinely single-occurrence, unlike ss_eligibility/ss_earnings_test/
        # ss_cola/wep_paragraph.
        self.assertEqual(set(shared_only_keys) & sm.REPEATED_KEY_ALLOWLIST, set())

    def test_summary_ss_note_is_unconditional(self):
        """summary_ss_note renders identically regardless of systemType — it
        must carry no system_type restriction at all."""
        _section, entry = sm.flatten_governed_keys()["srs_ss.summary_ss_note"]
        self.assertIsNone(entry.system_type)

    def test_wep_sentence_follows_summary_ss_note_in_the_shared_paragraph(self):
        """wep_sentence must be positioned after summary_ss_note within
        BRANCH_SHARED, and gated on CSRS/CSRS Offset + (documented)
        SSYearsEarning < 30 — not modeled as adjacent to/dependent on
        wep_paragraph."""
        flattened = sm.flatten_governed_keys()
        _s1, summary_ss_note = flattened["srs_ss.summary_ss_note"]
        _s2, wep_sentence = flattened["srs_ss.wep_sentence"]
        self.assertEqual(wep_sentence.positions[0].branch, sm.BRANCH_SHARED)
        self.assertGreater(wep_sentence.positions[0].position, summary_ss_note.positions[0].position)
        self.assertEqual(wep_sentence.system_type, ("CSRS", "CSRS Offset"))
        self.assertIn("SSYearsEarning", wep_sentence.description)
        self.assertIn("30", wep_sentence.description)

    def test_wep_paragraph_has_two_distinct_source_occurrences_transfers_and_csrs(self):
        """wep_paragraph: two genuine source occurrences — Transfers-only
        (nested inside the FERS/Transfers branch) and CSRS/CSRS-Offset-always
        (unconditional within that branch). Each occurrence's condition is a
        per-BranchPosition override, since a single blanket condition cannot
        express 'Transfers only' in one branch and 'always' in the other."""
        _section, entry = sm.flatten_governed_keys()["srs_ss.wep_paragraph"]
        self.assertEqual(len(entry.positions), 2)
        branches = {bp.branch for bp in entry.positions}
        self.assertEqual(branches, {sm.BRANCH_FERS_TRANSFERS, sm.BRANCH_CSRS_CSRS_OFFSET})
        self.assertIsNone(entry.system_type, "No single blanket system_type can describe both occurrences")
        by_branch = {bp.branch: bp for bp in entry.positions}
        self.assertEqual(by_branch[sm.BRANCH_FERS_TRANSFERS].system_type, ("Transfers",))
        self.assertEqual(by_branch[sm.BRANCH_CSRS_CSRS_OFFSET].system_type, ("CSRS", "CSRS Offset"))

    def test_gpo_paragraph_restricted_to_pure_csrs(self):
        _section, entry = sm.flatten_governed_keys()["srs_ss.gpo_paragraph"]
        self.assertEqual(entry.system_type, ("CSRS",))
        self.assertEqual(len(entry.positions), 1)
        self.assertEqual(entry.positions[0].branch, sm.BRANCH_CSRS_CSRS_OFFSET)

    def test_deferred_and_not_deferred_summary_variants_for_fers_transfers(self):
        flattened = sm.flatten_governed_keys()
        _s1, deferred = flattened["srs_ss.summary_deferred_note"]
        _s2, not_deferred = flattened["srs_ss.summary_earnings_test_note"]
        self.assertEqual(deferred.system_type, ("FERS", "Transfers"))
        self.assertEqual(deferred.retirement_type, ("Deferred",))
        self.assertEqual(not_deferred.system_type, ("FERS", "Transfers"))
        self.assertEqual(not_deferred.retirement_type, ("Regular", "VERA / DSR"))
        self.assertEqual(deferred.positions[0].branch, sm.BRANCH_SHARED)
        self.assertEqual(deferred.positions[0].position, not_deferred.positions[0].position)

    # --- resolve_outline() correctness per scenario ---

    def test_resolve_outline_pure_fers_excludes_wep_paragraph(self):
        outline_keys = [e.key for e in sm.resolve_outline("srs_ss", "FERS")]
        self.assertNotIn("srs_ss.wep_paragraph", outline_keys)
        self.assertNotIn("srs_ss.wep_sentence", outline_keys)
        self.assertNotIn("srs_ss.gpo_paragraph", outline_keys)
        self.assertIn("srs_ss.summary_ss_note", outline_keys)
        # summary_ss_note is always last for FERS/Transfers scenarios.
        self.assertEqual(outline_keys[-1], "srs_ss.summary_ss_note")

    def test_resolve_outline_transfers_includes_wep_paragraph(self):
        outline_keys = [e.key for e in sm.resolve_outline("srs_ss", "Transfers", "Deferred")]
        self.assertEqual(
            outline_keys,
            [
                "srs_ss.fers_purpose", "srs_ss.fers_eligibility", "srs_ss.fers_eligibility_exceptions",
                "srs_ss.fers_coverage_and_cost", "srs_ss.fers_receipt_of_payment", "srs_ss.fers_cola",
                "srs_ss.fers_earnings_test", "srs_ss.ss_eligibility", "srs_ss.ss_earnings_test",
                "srs_ss.ss_cola", "srs_ss.wep_paragraph", "srs_ss.summary_deferred_note",
                "srs_ss.summary_ss_note",
            ],
        )

    def test_resolve_outline_csrs_offset_includes_wep_paragraph_excludes_gpo_paragraph(self):
        """CSRS Offset: wep_paragraph renders (unconditional within this
        branch per Laravel Verification Section 2 Branch C); gpo_paragraph
        does not (pure-CSRS-only nested condition fails for CSRS Offset)."""
        outline_keys = [e.key for e in sm.resolve_outline("srs_ss", "CSRS Offset")]
        self.assertEqual(
            outline_keys,
            [
                "srs_ss.ss_eligibility", "srs_ss.ss_earnings_test", "srs_ss.ss_cola",
                "srs_ss.wep_paragraph", "srs_ss.summary_ss_note", "srs_ss.wep_sentence",
            ],
        )
        self.assertNotIn("srs_ss.gpo_paragraph", outline_keys)

    def test_resolve_outline_pure_csrs_includes_both_wep_paragraph_and_gpo_paragraph(self):
        """Pure CSRS: both wep_paragraph (always within this branch) and
        gpo_paragraph (pure-CSRS-only nested condition) render, per Laravel
        Verification Section 2 Branch D."""
        outline_keys = [e.key for e in sm.resolve_outline("srs_ss", "CSRS")]
        self.assertEqual(
            outline_keys,
            [
                "srs_ss.ss_eligibility", "srs_ss.ss_earnings_test", "srs_ss.ss_cola",
                "srs_ss.wep_paragraph", "srs_ss.gpo_paragraph", "srs_ss.summary_ss_note",
                "srs_ss.wep_sentence",
            ],
        )

    def test_resolve_outline_shared_content_always_follows_branch_specific_content(self):
        for system_type in sm.SYSTEM_TYPES:
            outline = sm.resolve_outline("srs_ss", system_type)
            branch = sm._branch_for_system_type(system_type)
            scopes = []
            for entry in outline:
                matching = [bp for bp in entry.positions if bp.branch in (branch, sm.BRANCH_SHARED)]
                scopes.append(0 if matching[0].branch == branch else 1)
            # Once scope becomes 1 (shared), it must never go back to 0 (branch-specific).
            self.assertEqual(scopes, sorted(scopes), f"{system_type}: shared content must follow branch content")

    def test_resolve_outline_rejects_unknown_system_type(self):
        with self.assertRaises(ValueError):
            sm.resolve_outline("srs_ss", "Not A Real System Type")

    def test_resolve_outline_works_for_non_branching_groups(self):
        """resolve_outline must also work for ordinary groups that only use
        BRANCH_DEFAULT (no real branch complexity), as a generic, reusable
        helper — not something special-cased to srs_ss only."""
        outline_keys = [e.key for e in sm.resolve_outline("pension", "FERS", "Deferred")]
        self.assertIn("pension.system_type_heading_fers", outline_keys)
        self.assertNotIn("pension.system_type_heading_non_fers", outline_keys)
        self.assertIn("pension.your_federal_pension_deferred", outline_keys)
        self.assertNotIn("pension.your_federal_pension_not_deferred", outline_keys)
        # FERS-only mra_explanation (position 3) is included and sits between
        # eligibility_to_retire (2) and day_of_month_to_retire (4).
        self.assertIn("pension.mra_explanation", outline_keys)
        self.assertEqual(
            outline_keys.index("pension.day_of_month_to_retire"),
            outline_keys.index("pension.mra_explanation") + 1,
        )
        self.assertEqual(
            outline_keys.index("pension.mra_explanation"),
            outline_keys.index("pension.eligibility_to_retire") + 1,
        )
        # For a non-FERS, non-deferred scenario, mra_explanation and the
        # deferred wording are both correctly excluded.
        csrs_outline_keys = [e.key for e in sm.resolve_outline("pension", "CSRS", "Regular")]
        self.assertNotIn("pension.mra_explanation", csrs_outline_keys)
        self.assertNotIn("pension.your_federal_pension_deferred", csrs_outline_keys)
        self.assertIn("pension.your_federal_pension_not_deferred", csrs_outline_keys)

    def test_tsp_and_irs_tie_order_for_required_scenarios(self):
        irs_precedence = [
            "irs_penalty.eligible_at_59_5",
            "irs_penalty.special_provision_meets_rules",
            "irs_penalty.special_provision_not_meets_rules",
            "irs_penalty.regular_not_meets_age55",
            "irs_penalty.regular_meets_age55",
        ]
        for system_type, retirement_type in (
            ("FERS", "Regular"),
            ("FERS", "Deferred"),
            ("CSRS", "Regular"),
            ("CSRS Offset", "Regular"),
        ):
            with self.subTest(system_type=system_type, retirement_type=retirement_type):
                tsp_keys = [
                    entry.key
                    for entry in sm.resolve_outline("tsp", system_type, retirement_type)
                    if entry.key in {
                        "tsp.match_threshold_sentence",
                        "tsp.agency_match_explanation",
                        "tsp.no_agency_match_csrs",
                    }
                ]
                if system_type in ("FERS", "Transfers"):
                    self.assertEqual(
                        tsp_keys,
                        ["tsp.match_threshold_sentence", "tsp.agency_match_explanation"],
                    )
                else:
                    self.assertEqual(tsp_keys, ["tsp.no_agency_match_csrs"])

                irs_keys = [
                    entry.key
                    for entry in sm.resolve_outline("irs_penalty", system_type, retirement_type)
                ]
                self.assertEqual(irs_keys, irs_precedence)

    def test_csrs_offset_tsp_no_agency_match_applicability(self):
        tsp_section = next(section for section in sm.PDF_STRUCTURE_MAP if section.group_key == "tsp")
        no_match_entry = next(
            entry for entry in tsp_section.entries if entry.key == "tsp.no_agency_match_csrs"
        )
        self.assertEqual(no_match_entry.system_type, ("CSRS", "CSRS Offset"))
        self.assertIn(
            "tsp.no_agency_match_csrs",
            [entry.key for entry in sm.resolve_outline("tsp", "CSRS Offset", "Regular")],
        )

    def test_resolve_outline_does_not_evaluate_display_condition_or_business_rules(self):
        """resolve_outline is presentation-only: it must not import or call
        anything from rules.py (the real Django display_condition engine).
        Checked structurally via bytecode name references, not by scanning
        prose/docstrings (which may legitimately mention these terms)."""
        self.assertNotIn("rules", sm.__dict__, "pdf_structure_map must not import fact_finder_content.rules")
        code_names = sm.resolve_outline.__code__.co_names
        self.assertNotIn("evaluate_rules", code_names)
        self.assertNotIn("display_condition", code_names)
        self.assertNotIn("AVAILABLE_FIELDS", code_names)


class IrsPenaltyReconciliationTests(unittest.TestCase):
    """Tests added for the Phase 1 Reconciliation: confirms the five IRS
    penalty variants and their verified precedence/conditions are
    documented, and that the FactFinderReportRenderer regression risk is
    recorded (without introducing new business-rule evaluation)."""

    def test_five_irs_penalty_keys_in_verified_precedence_order(self):
        irs_section = next(s for s in sm.PDF_STRUCTURE_MAP if s.group_key == "irs_penalty")
        ordered_keys = [e.key for e in irs_section.entries if e.kind is sm.SlotKind.GOVERNED]
        self.assertEqual(
            ordered_keys,
            [
                "irs_penalty.eligible_at_59_5",
                "irs_penalty.special_provision_meets_rules",
                "irs_penalty.special_provision_not_meets_rules",
                "irs_penalty.regular_not_meets_age55",
                "irs_penalty.regular_meets_age55",
            ],
        )
        # All five remain a documented 5-way tie at the same slot (selection
        # happens in Benefits Software PHP, not in this map).
        ties = sm.variant_tie_groups()
        self.assertEqual({e.key for e in ties[("irs_penalty", "default", 1)]}, set(ordered_keys))

    def test_irs_penalty_descriptions_document_verified_precedence_and_conditions(self):
        irs_section = next(s for s in sm.PDF_STRUCTURE_MAP if s.group_key == "irs_penalty")
        expected_precedence_fragments = {
            "irs_penalty.eligible_at_59_5": "Precedence 1 of 5",
            "irs_penalty.special_provision_meets_rules": "Precedence 2 of 5",
            "irs_penalty.special_provision_not_meets_rules": "Precedence 3 of 5",
            "irs_penalty.regular_not_meets_age55": "Precedence 4 of 5",
            "irs_penalty.regular_meets_age55": "Precedence 5 of 5",
        }
        for entry in irs_section.entries:
            self.assertIn(expected_precedence_fragments[entry.key], entry.description)
        # The old, now-resolved "not independently reverified" caveat must be gone.
        for entry in irs_section.entries:
            self.assertNotIn("not independently reverified", entry.description)

    def test_renderer_regression_risk_is_documented_not_evaluated(self):
        self.assertIsInstance(sm.IRS_PENALTY_RENDERER_REGRESSION_RISK, str)
        self.assertIn("FactFinderReportRenderer", sm.IRS_PENALTY_RENDERER_REGRESSION_RISK)
        self.assertIn("irsPenaltyContentKey", sm.IRS_PENALTY_RENDERER_REGRESSION_RISK)
        # Documentation only — must not be referenced by any function that
        # evaluates or filters content (i.e. it is inert data, not logic).
        import inspect
        self.assertNotIn(
            "IRS_PENALTY_RENDERER_REGRESSION_RISK", inspect.getsource(sm.resolve_outline),
        )


class StructureMapDjangoFixtureTests(TestCase):
    """DB-backed checks, using Django's isolated test database only (created
    and torn down per test run by the test runner) — never the developer's
    real LOCAL db.sqlite3. Fixtures are created per-test in setUp, mirroring
    the pattern already used in fact_finder_content/tests.py."""

    GROUP_LABELS = {
        "cover": "Cover",
        "pension": "Federal Pension",
        "sbp": "Survivor Benefit Plan",
        "srs_ss": "SRS & Social Security",
        "fegli": "FEGLI",
        "fehb": "FEHB",
        "fltcip": "FLTCIP",
        "tsp": "TSP",
        "irs_penalty": "IRS Early Withdrawal Penalty",
        "checklist": "Checklist",
    }

    def setUp(self):
        self.groups = {}
        for order, group_key in enumerate(sm.group_keys(), start=1):
            self.groups[group_key] = ContentBlockGroup.objects.create(
                key=group_key, label=self.GROUP_LABELS[group_key], display_order=order,
            )
        # Create one real ContentBlock row per mapped governed key, in its
        # declared group, so group-membership can be verified through the
        # real ORM relationship (not just string-prefix matching).
        for key, (section, _entry) in sm.flatten_governed_keys().items():
            ContentBlock.objects.create(key=key, group=self.groups[section.group_key], label=key)

    def test_group_keys_match_real_content_block_group_table(self):
        db_group_keys = set(ContentBlockGroup.objects.values_list("key", flat=True))
        self.assertEqual(set(sm.group_keys()), db_group_keys)

    def test_every_mapped_key_exists_in_its_expected_group(self):
        for key, (section, _entry) in sm.flatten_governed_keys().items():
            block = ContentBlock.objects.get(key=key)
            self.assertEqual(
                block.group.key, section.group_key,
                f"{key!r} is a real ContentBlock in group {block.group.key!r}, "
                f"but the structure map declares it under {section.group_key!r}",
            )

    def test_all_98_wired_keys_exist_as_real_content_blocks(self):
        existing_keys = set(ContentBlock.objects.values_list("key", flat=True))
        self.assertEqual(set(WIRED_BLOCK_KEYS), existing_keys)
