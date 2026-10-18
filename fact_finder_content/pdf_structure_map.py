"""
Fact Finder PDF content — admin presentation structure map (Phase 1).

Implements Option B from `PDF_CONTENT_STRUCTURE_MAP_DESIGN.md`: an immutable,
declarative description of WHERE each governed `ContentBlock.key` sits in the
real, static Fact Finder PDF reading order, for use by a future content-list
admin screen. It is a 1:1, hand-transcribed mapping of the already-verified
facts recorded in:

- `PDF_CONTENT_ARCHITECTURE_AUDIT.md` (the reconstructed section/within-group
  order, read directly from `report_pdf.blade.php`)
- `PDF_CONTENT_BLOCK_INVENTORY.csv` (the 98-key, per-group "Verified PDF
  Order" ground truth this module transcribes from)
- `PDF_CONTENT_RULES_MATRIX.md` (documents, but does not re-implement, the
  real `display_condition` rule registry)
- `PDF_CONTENT_EDITOR_GAP_ANALYSIS.md` and `PDF_CONTENT_LOCAL_DATABASE_VERIFICATION.md`
  (confirm group/key counts, unwired/inactive records)
- `PDF_CONTENT_STRUCTURE_MAP_DESIGN.md` (the design this module implements —
  see "Deviations from the design document" below for the few places this
  module intentionally does NOT follow that document's illustrative code)

What this module IS:
- A read-only, presentation-order outline consulted by a future content-list
  screen to group/sequence rows the way the real PDF reads.

What this module explicitly is NOT, and must never become:
- It does not store or duplicate `ContentBlockVersion.body_html` wording —
  every `key` below is only a pointer to a real `ContentBlock.key`.
- It does not evaluate, replace, or override `ContentBlock.display_condition`
  — the `system_type`/`retirement_type`/`description` annotations below are
  documentation-only tooltips, transcribed from the Inventory CSV, not a
  second rule engine.
- It does not perform any business calculation.
- It has zero effect on the generated PDF — `report_pdf.blade.php` remains
  the sole source of truth for real rendering order and content (Architecture
  Audit Section 3.3: `benefits-software` already discards the resolve-content
  API's `order` field entirely).
- It does not change `views.py`, `views_api.py`, any template, the resolve-
  content API contract, or content publication/versioning. This module is not
  imported by any of them as of this phase.

Deviations from `PDF_CONTENT_STRUCTURE_MAP_DESIGN.md` (resolved inconsistencies):

1. **`srs_ss.summary_ss_note` is modeled with a single verified position, not
   two.** The design document's Section 4.1/4.2 narrative and illustrative
   code assert this key renders a second time in the CSRS/CSRS Offset branch
   (after `gpo_paragraph`). However `PDF_CONTENT_BLOCK_INVENTORY.csv`'s
   "Verified PDF Order" column documents only ONE position for this key
   ("13 (always rendered after the conditional fragment above)"), with no
   "X / Y" dual-position notation of the kind used for `ss_eligibility`,
   `ss_earnings_test`, `ss_cola`, and `wep_paragraph` (which DO carry that
   notation). Its own "Retirement System Conditions"/"Retirement Type
   Conditions" columns are both `None` ("Always shown"), unlike a branch-
   scoped key. Per this phase's instruction not to assume every design-
   document detail is correct and to resolve inconsistencies explicitly,
   this module represents only the CSV-verified single position
   (`BRANCH_FERS_TRANSFERS`, 13) and does NOT invent a second
   `BRANCH_CSRS_CSRS_OFFSET` occurrence. See the `srs_ss` section below for
   the full note. Consequently `REPEATED_KEY_ALLOWLIST` below has 4 members,
   not the 5 the design document anticipated.
2. **`srs_ss.wep_sentence`'s single verified position (14) is kept verbatim**,
   even though it does not continue the CSRS/CSRS Offset branch's own local
   1-5 restart count (`gpo_paragraph` = 5) contiguously. This numbering
   discontinuity is not resolved by any available evidence (no access to
   `report_pdf.blade.php` in this phase) and is documented as an open
   question rather than silently renumbered.
3. **Ungoverned sections use a dedicated `UngovernedSection` type**, separate
   from `ReportSection`/`SlotEntry`, because the design document defined
   `SlotKind.UNGOVERNED` in its illustrative dataclass sketch but never
   worked through a concrete representation for a whole PDF section with no
   `ContentBlockGroup` at all (its own Outstanding Business Decision #4
   left this explicitly undecided). `SlotKind` in this module therefore has
   only `GOVERNED` and `COMPUTED` members.
4. **Computed placeholders carry an explicit `placeholder_id`** (e.g.
   `"computed:pension.full_eligibility_requirements_table"`), not just a
   `label`. This satisfies this phase's requirement for "stable placeholder
   identifiers that cannot be mistaken for `ContentBlock.key` values" — real
   `ContentBlock.key` values never contain a colon, so the `"computed:"`
   prefix is a structurally safe, unambiguous marker.
5. **`INACTIVE_BLOCK_KEYS` is a new, explicit registry** not present in the
   design document's sketch, added to satisfy this phase's requirement to
   separately identify inactive content records. Per
   `PDF_CONTENT_LOCAL_DATABASE_VERIFICATION.md` Section 3.2, exactly one key
   (`fegli.basic_description`) is known-inactive; it appears nowhere in
   `PDF_STRUCTURE_MAP` (neither as a governed entry nor as an unwired key).

Everything else below is a direct, mechanical transcription of the verified
CSV/audit data — not new research.

---

Phase 1 Reconciliation (Laravel Source Verification) — corrections applied
after `docs/PDF_CONTENT_EDITOR_PHASE1_LARAVEL_VERIFICATION.md` (a direct,
read-only reading of `benefits-software`'s real `report_pdf.blade.php` and
`EmployeeController@createPdfFEGLI`) became available. That report is
authoritative for the specific rendering behaviors it directly verified and
supersedes the CSV/this module's original Phase 1 guesses wherever they
conflict. Per that reconciliation:

- **Confirmed already correct, unchanged:** `srs_ss.summary_ss_note` single-
  occurrence modeling (the Phase 1 deviation from the design document's
  5-dual-key assumption was independently validated as correct — the
  Laravel verification explicitly confirms "NOT duplicated"), `srs_ss.
  gpo_paragraph`'s pure-CSRS-only gating, `srs_ss.wep_paragraph`'s two
  genuine source occurrences (Transfers-only / CSRS-CSRS-Offset-always),
  all 98 wired keys, all 10 groups, `REPEATED_KEY_ALLOWLIST`'s 4 members,
  and the 5 `irs_penalty.*` keys and their relative precedence.
- **Corrected:** `srs_ss.summary_deferred_note`, `summary_earnings_test_note`,
  `summary_ss_note`, and `wep_sentence` were re-modeled from ad hoc
  per-branch `BranchPosition`s (an artifact of Phase 1's CSV-only
  numbering, which conflated a branch-specific count with a separate
  shared-tail count) onto a new `BRANCH_SHARED` scope — these four keys
  live in one unconditional shared `<p>` block in the real source,
  reached only *after* both system-type `@if` blocks close, not nested
  inside either one. A new `resolve_outline()` helper computes each
  system type's correct effective rendering sequence from this corrected
  data. See the `srs_ss` section below and
  `CSV_POSITION_SUPERSEDED_BY_LARAVEL_VERIFICATION` for the specific,
  itemized divergence from the original CSV's literal position numbers for
  just these four keys.
- **Corrected:** the Pension and FEGLI "whichever variant rendered"
  calculated-table placeholders now anchor to the deferred/not-deferred
  variant pair as a single unit (`anchor_after_variant_group`), not to one
  individual variant key.
- **Corrected:** the single SBP survivor-benefit computed placeholder was
  split into two separate, mutually-exclusive, branch-specific placeholders
  (55%/partial for FERS/Transfers; 50%/25% for CSRS/CSRS Offset) — they are
  two structurally different tables in the real source, not one reused
  table. This raises the total computed-placeholder count from 11 to 12.
- **Documented, not code-changed:** the IRS penalty entries' descriptions
  were expanded with the verified precedence order and exact qualifying
  conditions (`EmployeeController.php` lines 1560-1629); the previously
  added "not independently reverified" caveat was removed now that this
  has been independently verified. The `FactFinderReportRenderer` governed-
  content gap (a `benefits-software`-side regression-testing risk, not an
  Advisor Portal defect) is recorded as `IRS_PENALTY_RENDERER_REGRESSION_RISK`
  — a documentation-only constant, not a new rule evaluated by this module.

This reconciliation did not change: `PDF_STRUCTURE_MAP`'s 10 groups, the 98
wired keys, `INACTIVE_BLOCK_KEYS`, `UNGOVERNED_SECTIONS`, or any group other
than `srs_ss`/`pension`/`sbp`/`fegli`/`irs_penalty` (and `irs_penalty` only
at the description/documentation level, not structurally).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple

from .wiring_status import WIRED_BLOCK_KEYS


class SlotKind(str, Enum):
    """What occupies one position in the structure map.

    GOVERNED — a real, editable `ContentBlock.key`.
    COMPUTED — a non-editable, per-case calculated table/placeholder with no
        corresponding `ContentBlock` row at all.
    """

    GOVERNED = "governed"
    COMPUTED = "computed"


# A branch name is a short, documentation-only label for one of
# `report_pdf.blade.php`'s real @if/@elseif narrative paths. It is NOT a
# Django DB value and nothing evaluates it at runtime — it exists only so a
# single key can be declared at more than one physical position when (and
# only when) the audit evidence supports that. Every group except `srs_ss`
# uses only `BRANCH_DEFAULT`.
BRANCH_DEFAULT = "default"
BRANCH_FERS_TRANSFERS = "fers_transfers"
BRANCH_CSRS_CSRS_OFFSET = "csrs_csrs_offset"

# BRANCH_SHARED: a key whose SOURCE occurs exactly once, unconditionally,
# OUTSIDE any system-type-specific @if block (reached regardless of which
# branch — if any — rendered above it), but whose own gating condition
# (system_type/retirement_type on the SlotEntry) may still restrict which
# scenarios actually show its content. This is distinct from BRANCH_DEFAULT
# (used by groups with no branching at all) and from a per-branch
# BranchPosition (used for content genuinely duplicated/nested inside one
# specific @if block). Verified in
# docs/PDF_CONTENT_EDITOR_PHASE1_LARAVEL_VERIFICATION.md Section 2 for
# srs_ss's shared closing paragraph (summary_deferred_note,
# summary_earnings_test_note, summary_ss_note, wep_sentence) — the only
# group that uses this branch as of this phase.
BRANCH_SHARED = "shared"

SYSTEM_TYPES = ("FERS", "Transfers", "CSRS", "CSRS Offset")
RETIREMENT_TYPES = ("Regular", "VERA / DSR", "Deferred")


@dataclass(frozen=True)
class BranchPosition:
    """One (branch, position) pairing. A `SlotEntry` normally has exactly one
    of these. It has more than one only for the narrow, CSV-verified case of
    a key whose physical position differs by retirement-system branch.

    `system_type`, when set, OVERRIDES the parent `SlotEntry.system_type` for
    just this one occurrence — needed for the rare, verified case (e.g.
    `srs_ss.wep_paragraph`) where the same key's real gating condition
    genuinely differs per branch (Transfers-only inside the FERS/Transfers
    branch; unconditional inside the CSRS/CSRS Offset branch). When `None`,
    the entry's own `system_type` applies to this occurrence as usual. This
    is the concrete mechanism that lets `resolve_outline()` (below) compute
    the correct effective applicability per branch from a single declared
    source occurrence, rather than one blanket condition misapplied to every
    occurrence of a key."""

    branch: str
    position: int
    note: str = ""
    system_type: Optional[Tuple[str, ...]] = None


@dataclass(frozen=True)
class SlotEntry:
    """One occupant of one (group, branch, position) slot.

    Multiple `SlotEntry` objects may legitimately share the same
    (branch, position) within a `ReportSection` — that is how mutually-
    exclusive narrative variants are represented: as a documented tie, not an
    error (see `variant_tie_groups()` below).
    """

    kind: SlotKind
    positions: Tuple[BranchPosition, ...]
    key: Optional[str] = None
    placeholder_id: Optional[str] = None
    label: str = ""
    system_type: Optional[Tuple[str, ...]] = None
    retirement_type: Optional[Tuple[str, ...]] = None
    anchor_after: Optional[str] = None
    anchor_after_variant_group: Optional[Tuple[str, ...]] = None
    description: str = ""

    def __post_init__(self):
        if self.kind is SlotKind.GOVERNED:
            if not self.key:
                raise ValueError("GOVERNED entries require a real ContentBlock.key")
            if self.placeholder_id is not None:
                raise ValueError(f"GOVERNED entry {self.key!r} must not carry a placeholder_id")
            if self.anchor_after is not None or self.anchor_after_variant_group is not None:
                raise ValueError(f"GOVERNED entry {self.key!r} must not carry an anchor — anchors are COMPUTED-only")
        elif self.kind is SlotKind.COMPUTED:
            if self.key is not None:
                raise ValueError(
                    f"COMPUTED entry {self.placeholder_id!r} must not reference a ContentBlock.key"
                )
            if not self.placeholder_id:
                raise ValueError("COMPUTED entries require a stable placeholder_id")
            if not self.placeholder_id.startswith("computed:"):
                raise ValueError(
                    f"COMPUTED placeholder_id {self.placeholder_id!r} must start with 'computed:' "
                    "so it can never be mistaken for a real ContentBlock.key"
                )
            if self.anchor_after is not None and self.anchor_after_variant_group is not None:
                raise ValueError(
                    f"COMPUTED placeholder {self.placeholder_id!r} must set exactly one of "
                    "anchor_after / anchor_after_variant_group, not both"
                )
            if self.anchor_after is None and self.anchor_after_variant_group is None:
                raise ValueError(
                    f"COMPUTED placeholder {self.placeholder_id!r} requires an anchor "
                    "(anchor_after or anchor_after_variant_group)"
                )
            if self.anchor_after_variant_group is not None and len(self.anchor_after_variant_group) < 2:
                raise ValueError(
                    f"COMPUTED placeholder {self.placeholder_id!r}'s anchor_after_variant_group must "
                    "name 2+ keys (a variant group, not a single key — use anchor_after for that)"
                )


@dataclass(frozen=True)
class ReportSection:
    """One of the 10 governed `ContentBlockGroup`s, in verified PDF order."""

    group_key: str
    section_label: str
    entries: Tuple[SlotEntry, ...]
    unwired_keys: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class UngovernedSection:
    """A whole real PDF section with no `ContentBlockGroup` at all — never
    editable through this panel, under any key. `after_group`/`before_group`
    record only what the architecture audit's section-banner reconstruction
    actually verified (an adjacency to governed sections' physical line
    ranges), not an invented absolute position."""

    label: str
    after_group: Optional[str] = None
    before_group: Optional[str] = None
    description: str = ""


# ---------------------------------------------------------------------------
# Section 1: cover
# ---------------------------------------------------------------------------

_COVER = ReportSection(
    group_key="cover",
    section_label="Cover Page",
    entries=(
        SlotEntry(
            kind=SlotKind.GOVERNED,
            key="cover.title",
            label="Cover page title",
            positions=(BranchPosition(BRANCH_DEFAULT, 1),),
        ),
    ),
)

# ---------------------------------------------------------------------------
# Section 2: pension (Federal Pension)
# ---------------------------------------------------------------------------

_PENSION = ReportSection(
    group_key="pension",
    section_label="Federal Pension",
    entries=(
        SlotEntry(
            kind=SlotKind.GOVERNED, key="pension.system_type_heading_fers",
            label="FERS system-type heading",
            positions=(BranchPosition(BRANCH_DEFAULT, 1),),
            system_type=("FERS",),
            description="Mutually exclusive with system_type_heading_non_fers",
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="pension.system_type_heading_non_fers",
            label="Non-FERS (CSRS/CSRS Offset/Transfers) system-type heading",
            positions=(BranchPosition(BRANCH_DEFAULT, 1),),
            system_type=("CSRS", "CSRS Offset", "Transfers"),
            description="Same slot as system_type_heading_fers",
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="pension.eligibility_to_retire",
            label="Eligibility to Retire",
            positions=(BranchPosition(BRANCH_DEFAULT, 2),),
        ),
        SlotEntry(
            kind=SlotKind.COMPUTED,
            placeholder_id="computed:pension.full_eligibility_requirements_table",
            label="Full Eligibility Requirements table (computed)",
            positions=(),
            anchor_after="pension.eligibility_to_retire",
            description="Calculated per-case; not editable — no ContentBlock exists for it.",
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="pension.mra_explanation",
            label="Minimum Retirement Age (MRA) explanation",
            positions=(BranchPosition(BRANCH_DEFAULT, 3),),
            system_type=("FERS",),
            description="FERS only — non-FERS cases skip this block entirely",
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="pension.day_of_month_to_retire",
            label="Day of the Month to Retire",
            positions=(BranchPosition(BRANCH_DEFAULT, 4),),
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="pension.calculating_the_federal_pension",
            label="Calculating the Federal Pension",
            positions=(BranchPosition(BRANCH_DEFAULT, 5),),
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="pension.high3_average_salary",
            label="High-3 Average Salary",
            positions=(BranchPosition(BRANCH_DEFAULT, 6),),
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="pension.high3_pay_included_table",
            label="High-3 pay included/not-included table",
            positions=(BranchPosition(BRANCH_DEFAULT, 7),),
            description="Category B governed structural table, not a computed placeholder",
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="pension.applying_unused_sick_leave",
            label="Applying Unused Sick Leave",
            positions=(BranchPosition(BRANCH_DEFAULT, 8),),
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="pension.selling_back_annual_leave",
            label="Selling Back Annual Leave",
            positions=(BranchPosition(BRANCH_DEFAULT, 9),),
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="pension.part_time_service",
            label="Part-time Service",
            positions=(BranchPosition(BRANCH_DEFAULT, 10),),
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="pension.cost_of_living_adjustments",
            label="Cost of Living Adjustments (COLAs)",
            positions=(BranchPosition(BRANCH_DEFAULT, 11),),
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="pension.your_federal_pension_deferred",
            label="Your Federal Pension (deferred-retirement wording)",
            positions=(BranchPosition(BRANCH_DEFAULT, 12),),
            retirement_type=("Deferred",),
            description="Mutually exclusive with your_federal_pension_not_deferred",
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="pension.your_federal_pension_not_deferred",
            label="Your Federal Pension (immediate-retirement wording)",
            positions=(BranchPosition(BRANCH_DEFAULT, 12),),
            retirement_type=("Regular", "VERA / DSR"),
            description="Same slot as your_federal_pension_deferred",
        ),
        SlotEntry(
            kind=SlotKind.COMPUTED,
            placeholder_id="computed:pension.multi_scenario_pension_projection_table",
            label="Multi-scenario pension projection table (computed)",
            positions=(),
            anchor_after_variant_group=(
                "pension.your_federal_pension_deferred",
                "pension.your_federal_pension_not_deferred",
            ),
            description=(
                "Calculated per-case; not editable. CONFIRMED (Laravel Verification Section 4): a "
                "single, unconditional, non-duplicated table — one physical table in source, reached "
                "regardless of which of the two mutually exclusive narrative variants rendered. "
                "Anchored to the variant pair AS A WHOLE (anchor_after_variant_group), not to one "
                "individual variant, since anchoring to only one would incorrectly imply the table is "
                "absent or differently positioned for the other case."
            ),
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="pension.planned_delayed_retirement_intro",
            label="Planned & Delayed Retirement intro",
            positions=(BranchPosition(BRANCH_DEFAULT, 13),),
            retirement_type=("Regular", "VERA / DSR"),
            description="Only rendered when retirementType != Deferred",
        ),
        SlotEntry(
            kind=SlotKind.COMPUTED,
            placeholder_id="computed:pension.five_year_delayed_retirement_projection_table",
            label="5-year delayed-retirement projection table (computed)",
            positions=(),
            anchor_after="pension.planned_delayed_retirement_intro",
            description="Calculated per-case; not editable.",
        ),
    ),
)

# ---------------------------------------------------------------------------
# Section 3: sbp (Survivor Benefit Plan)
# ---------------------------------------------------------------------------

_SBP = ReportSection(
    group_key="sbp",
    section_label="Survivor Benefit Plan (SBP)",
    entries=(
        SlotEntry(kind=SlotKind.GOVERNED, key="sbp.eligibility",
                   label="SBP Eligibility", positions=(BranchPosition(BRANCH_DEFAULT, 1),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="sbp.coverage_and_cost",
                   label="SBP Coverage & Cost", positions=(BranchPosition(BRANCH_DEFAULT, 2),)),
        SlotEntry(
            kind=SlotKind.COMPUTED,
            placeholder_id="computed:sbp.level_amount_cost_table",
            label="Level/Amount/Cost table (computed)",
            positions=(),
            anchor_after="sbp.coverage_and_cost",
            description=(
                "Calculated per-case; rows differ FERS+Transfers vs. CSRS/CSRS Offset via a "
                "blade @if, not a governed block."
            ),
        ),
        SlotEntry(kind=SlotKind.GOVERNED, key="sbp.changes_in_retirement",
                   label="SBP Changes in Retirement", positions=(BranchPosition(BRANCH_DEFAULT, 3),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="sbp.connection_to_fehb_current_spouse",
                   label="Connection to FEHB for a Current Spouse",
                   positions=(BranchPosition(BRANCH_DEFAULT, 4),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="sbp.spouse_passes_away_first",
                   label="What if Your Spouse Passes Away First",
                   positions=(BranchPosition(BRANCH_DEFAULT, 5),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="sbp.considerations_federal_couples",
                   label="Considerations for Federal Couples",
                   positions=(BranchPosition(BRANCH_DEFAULT, 6),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="sbp.retiring_under_deferred_scenario",
                   label="Retiring Under a Deferred Retirement Scenario",
                   positions=(BranchPosition(BRANCH_DEFAULT, 7),)),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="sbp.deferred_intro",
            label="Your Spouse's Survivor Benefit intro (FERS/Transfers, deferred)",
            positions=(BranchPosition(BRANCH_DEFAULT, 8),),
            system_type=("FERS", "Transfers"), retirement_type=("Deferred",),
            description="3-way tie at position 8 with fers_transfers_intro_not_deferred and csrs_intro",
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="sbp.fers_transfers_intro_not_deferred",
            label="Your Spouse's Survivor Benefit intro (FERS/Transfers, not deferred)",
            positions=(BranchPosition(BRANCH_DEFAULT, 8),),
            system_type=("FERS", "Transfers"), retirement_type=("Regular", "VERA / DSR"),
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="sbp.csrs_intro",
            label="Your Spouse's Survivor Benefit intro (CSRS/CSRS Offset)",
            positions=(BranchPosition(BRANCH_DEFAULT, 8),),
            system_type=("CSRS", "CSRS Offset"),
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="sbp.levels_fers_transfers",
            label="SBP Levels table (FERS/Transfers)",
            positions=(BranchPosition(BRANCH_DEFAULT, 9),),
            system_type=("FERS", "Transfers"),
            description="Category B governed table; tie at position 9 with levels_csrs",
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="sbp.levels_csrs",
            label="SBP Levels table (CSRS/CSRS Offset)",
            positions=(BranchPosition(BRANCH_DEFAULT, 9),),
            system_type=("CSRS", "CSRS Offset"),
        ),
        SlotEntry(
            kind=SlotKind.COMPUTED,
            placeholder_id="computed:sbp.survivor_benefit_projection_table_fers_transfers",
            label="Full (55%) / partial survivor-benefit projection table — FERS/Transfers (computed)",
            positions=(),
            anchor_after="sbp.levels_fers_transfers",
            system_type=("FERS", "Transfers"),
            description=(
                "Calculated per-case; not editable. CORRECTED (Laravel Verification Section 5): this is "
                "NOT the same table instance as the CSRS/CSRS Offset variant below — it is a structurally "
                "different table (55% full-survivor-benefit / partial-benefit columns, using the "
                "monthly_survivor_benefits_55/_partial fields), physically nested inside the FERS/Transfers "
                "@if branch immediately after sbp.levels_fers_transfers. Mutually exclusive with "
                "survivor_benefit_projection_table_csrs — never both present in one generated PDF."
            ),
        ),
        SlotEntry(
            kind=SlotKind.COMPUTED,
            placeholder_id="computed:sbp.survivor_benefit_projection_table_csrs",
            label="Full (50%) / partial (25%) survivor-benefit projection table — CSRS/CSRS Offset (computed)",
            positions=(),
            anchor_after="sbp.levels_csrs",
            system_type=("CSRS", "CSRS Offset"),
            description=(
                "Calculated per-case; not editable. CORRECTED (Laravel Verification Section 5): a "
                "structurally different table from the FERS/Transfers variant above (50% full-survivor-"
                "benefit / 25% partial-benefit columns, using the monthly_survivor_benefits_50/_25 fields), "
                "physically nested inside the CSRS/CSRS Offset @elseif branch immediately after "
                "sbp.levels_csrs. Mutually exclusive with survivor_benefit_projection_table_fers_transfers "
                "— never both present in one generated PDF."
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# Section 4: srs_ss (Special Retirement Supplement & Social Security)
# ---------------------------------------------------------------------------
# The critical case. See the module docstring's "Deviations" items 1-2 (the
# original Phase 1 reasoning) and "Phase 1 Reconciliation" (the corrections
# applied after docs/PDF_CONTENT_EDITOR_PHASE1_LARAVEL_VERIFICATION.md became
# available) for the full history of how this section's modeling evolved.
#
# Verified source structure (Laravel Verification Section 2):
#   - Two independent, sequential, system-type-gated @if blocks
#     (FERS/Transfers; CSRS/CSRS Offset) — each with its own nested content.
#   - ONE shared, unconditional closing <p> block (line 1310) reached AFTER
#     both @if blocks close, containing (in this order):
#       1. summary_deferred_note / summary_earnings_test_note (tie, FERS or
#          Transfers only, by deferred status)
#       2. summary_ss_note (unconditional — renders for all 4 system types)
#       3. wep_sentence (CSRS/CSRS Offset only, further gated by
#          SSYearsEarning < 30 via an inline PHP ternary)
#   BRANCH_SHARED models this one shared <p> block as a position scope of its
#   own, distinct from the two per-system-type BranchPosition scopes used for
#   content genuinely duplicated/nested inside one specific @if block.

_SRS_SS = ReportSection(
    group_key="srs_ss",
    section_label="Special Retirement Supplement & Social Security",
    entries=(
        # --- FERS/Transfers-exclusive SRS sub-section (positions 1-7) ---
        SlotEntry(kind=SlotKind.GOVERNED, key="srs_ss.fers_purpose",
                   label="FERS SRS Purpose",
                   positions=(BranchPosition(BRANCH_FERS_TRANSFERS, 1),),
                   system_type=("FERS", "Transfers"),
                   description="Entire FERS SRS sub-section (positions 1-7) only renders for FERS/Transfers"),
        SlotEntry(kind=SlotKind.GOVERNED, key="srs_ss.fers_eligibility",
                   label="FERS SRS Eligibility (paragraph 1)",
                   positions=(BranchPosition(BRANCH_FERS_TRANSFERS, 2),),
                   system_type=("FERS", "Transfers")),
        SlotEntry(kind=SlotKind.GOVERNED, key="srs_ss.fers_eligibility_exceptions",
                   label="FERS SRS Eligibility (paragraph 2 — exceptions)",
                   positions=(BranchPosition(BRANCH_FERS_TRANSFERS, 3),),
                   system_type=("FERS", "Transfers"),
                   description="Split from a single original 2-paragraph block to match the template's "
                               "two separate <tr><td> rows"),
        SlotEntry(kind=SlotKind.GOVERNED, key="srs_ss.fers_coverage_and_cost",
                   label="FERS SRS Coverage and Cost",
                   positions=(BranchPosition(BRANCH_FERS_TRANSFERS, 4),),
                   system_type=("FERS", "Transfers")),
        SlotEntry(kind=SlotKind.GOVERNED, key="srs_ss.fers_receipt_of_payment",
                   label="FERS SRS Receipt of Payment",
                   positions=(BranchPosition(BRANCH_FERS_TRANSFERS, 5),),
                   system_type=("FERS", "Transfers")),
        SlotEntry(kind=SlotKind.GOVERNED, key="srs_ss.fers_cola",
                   label="FERS SRS Cost of Living Adjustments",
                   positions=(BranchPosition(BRANCH_FERS_TRANSFERS, 6),),
                   system_type=("FERS", "Transfers")),
        SlotEntry(kind=SlotKind.GOVERNED, key="srs_ss.fers_earnings_test",
                   label="FERS SRS Earnings Test",
                   positions=(BranchPosition(BRANCH_FERS_TRANSFERS, 7),),
                   system_type=("FERS", "Transfers")),

        # --- Shared Social Security content: one key, two BranchPositions each ---
        # (CSV-verified via explicit "X / Y" dual-position notation; independently
        # re-confirmed as 2 genuine source occurrences per key in Laravel
        # Verification Section 3.)
        SlotEntry(kind=SlotKind.GOVERNED, key="srs_ss.ss_eligibility",
                   label="Social Security Eligibility",
                   positions=(
                       BranchPosition(BRANCH_FERS_TRANSFERS, 8),
                       BranchPosition(BRANCH_CSRS_CSRS_OFFSET, 1, note="Separate page; first item in this branch"),
                   ),
                   description="Reused across both system-type branches on different physical pages"),
        SlotEntry(kind=SlotKind.GOVERNED, key="srs_ss.ss_earnings_test",
                   label="Social Security Earnings Test",
                   positions=(
                       BranchPosition(BRANCH_FERS_TRANSFERS, 9),
                       BranchPosition(BRANCH_CSRS_CSRS_OFFSET, 2),
                   )),
        SlotEntry(kind=SlotKind.GOVERNED, key="srs_ss.ss_cola",
                   label="Social Security Cost of Living Adjustments",
                   positions=(
                       BranchPosition(BRANCH_FERS_TRANSFERS, 10),
                       BranchPosition(BRANCH_CSRS_CSRS_OFFSET, 3),
                   )),

        # --- WEP: same key, two DIFFERENT gating conditions per branch — CONFIRMED
        # (Laravel Verification Section 3): mutually exclusive by construction, not
        # merely by data. Pure FERS (non-Transfers) reaches neither occurrence.
        # Uses BranchPosition.system_type (per-occurrence override) rather than a
        # blanket entry-level system_type, since the two occurrences' conditions
        # genuinely differ — a single blanket condition would incorrectly exclude
        # this key from the CSRS/CSRS Offset outline entirely. ---
        SlotEntry(kind=SlotKind.GOVERNED, key="srs_ss.wep_paragraph",
                   label="Windfall Elimination Provision (WEP) paragraph",
                   positions=(
                       BranchPosition(BRANCH_FERS_TRANSFERS, 11,
                                       note="Transfers only within this branch (not FERS)",
                                       system_type=("Transfers",)),
                       BranchPosition(BRANCH_CSRS_CSRS_OFFSET, 4,
                                       note="Always within this branch",
                                       system_type=("CSRS", "CSRS Offset")),
                   ),
                   description="Same text key used for 2 different gating conditions depending on which "
                               "system-type branch it is in — each BranchPosition carries its own "
                               "system_type override (Transfers only in the FERS/Transfers branch; "
                               "CSRS/CSRS Offset, unconditionally, in that branch). "
                               "Verified: pure FERS (non-Transfers) reaches neither occurrence — wep_paragraph "
                               "is absent entirely for pure FERS (Laravel Verification Section 2, Branch A)."),

        # --- GPO: CSRS/CSRS Offset branch ONLY, pure CSRS (narrower than the branch itself).
        # CONFIRMED correct as originally modeled — no change (Laravel Verification Section 8
        # item 4: "if the current map applies it to CSRS/CSRS Offset as a pair, that is
        # incorrect" — it does not; it was already restricted to pure CSRS only). ---
        SlotEntry(kind=SlotKind.GOVERNED, key="srs_ss.gpo_paragraph",
                   label="Government Pension Offset (GPO) paragraph",
                   positions=(BranchPosition(BRANCH_CSRS_CSRS_OFFSET, 5),),
                   system_type=("CSRS",),
                   description="Narrower than its parent branch — excludes CSRS Offset even though it is "
                               "in the same outer @elseif"),

        # --- Shared closing paragraph (BRANCH_SHARED): one unconditional <p> block (line
        # 1310) reached AFTER both system-type @if blocks close — NOT nested inside either
        # one. Corrected in the Phase 1 Reconciliation from the original per-branch
        # BranchPosition modeling (see module docstring). Order within this shared scope,
        # per Laravel Verification Section 2: (1) deferred/earnings-test tie, (2)
        # summary_ss_note (unconditional), (3) wep_sentence (CSRS/CSRS Offset only). ---
        SlotEntry(kind=SlotKind.GOVERNED, key="srs_ss.summary_deferred_note",
                   label="SRS/SS summary — deferred-retiree note",
                   positions=(BranchPosition(BRANCH_SHARED, 1),),
                   system_type=("FERS", "Transfers"), retirement_type=("Deferred",),
                   description="Tie at shared position 1 with summary_earnings_test_note; part of the one "
                               "shared closing paragraph, not nested inside the FERS/Transfers @if block"),
        SlotEntry(kind=SlotKind.GOVERNED, key="srs_ss.summary_earnings_test_note",
                   label="SRS/SS summary — earnings-test note",
                   positions=(BranchPosition(BRANCH_SHARED, 1),),
                   system_type=("FERS", "Transfers"), retirement_type=("Regular", "VERA / DSR")),

        # --- summary_ss_note: CONFIRMED a single, unconditional source occurrence — the
        # Phase 1 deviation from the design document (which assumed a second CSRS-branch
        # occurrence) was independently validated as correct by Laravel Verification
        # Section 3: "confirmed NOT duplicated... renders for all four systemType values,
        # at the same single position". Re-scoped from BRANCH_FERS_TRANSFERS to
        # BRANCH_SHARED in the Phase 1 Reconciliation, since its one true source location
        # is outside both system-type branches, not inside the FERS/Transfers one. ---
        SlotEntry(kind=SlotKind.GOVERNED, key="srs_ss.summary_ss_note",
                   label="SRS/SS summary — Social Security note",
                   positions=(
                       BranchPosition(BRANCH_SHARED, 2,
                                       note="Unconditional; renders for all 4 system types, immediately after "
                                            "whichever (if any) of the deferred/earnings-test tie rendered"),
                   ),
                   description=(
                       "CONFIRMED single source occurrence (Laravel Verification Section 1 finding 1, "
                       "Section 3): lives in the one shared <p> block (line 1310), reached after both "
                       "system-type @if blocks close; renders identically regardless of systemType. "
                       "Contains an embedded dynamic value ({$ss_arr['ss_cola']}) composed into the "
                       "fallback literal."
                   )),

        # --- wep_sentence: CONFIRMED a single source occurrence, in the SAME shared <p>
        # block as summary_ss_note (not CSRS-branch-nested as Phase 1 originally modeled),
        # immediately after it, gated on (systemType IN ('CSRS','CSRS Offset')) AND
        # (SSYearsEarning < 30) via an inline PHP ternary. Re-scoped from
        # BRANCH_CSRS_CSRS_OFFSET to BRANCH_SHARED in the Phase 1 Reconciliation; the
        # Phase 1 "numbering discontinuity" note (position 14 not contiguous with
        # gpo_paragraph's local 1-5 count) is resolved by this correction: wep_sentence was
        # never part of that branch's local count at all. ---
        SlotEntry(kind=SlotKind.GOVERNED, key="srs_ss.wep_sentence",
                   label="SRS/SS summary — WEP penalty sentence fragment",
                   positions=(
                       BranchPosition(BRANCH_SHARED, 3,
                                       note="Last element of the shared closing paragraph, immediately after "
                                            "summary_ss_note; has no positional relationship to wep_paragraph, "
                                            "which is a separate key rendered earlier inside the branch-"
                                            "specific SRS/SS detail tables"),
                   ),
                   system_type=("CSRS", "CSRS Offset"),
                   description="Gated by a raw PHP ternary (SSYearsEarning < 30), not a Django rule — "
                               "easy to miss when reading the template casually. Verified: not adjacent to "
                               "wep_paragraph (Laravel Verification Section 1 finding 2)."),
    ),
)

# ---------------------------------------------------------------------------
# Section 5: fegli
# ---------------------------------------------------------------------------

_FEGLI = ReportSection(
    group_key="fegli",
    section_label="Federal Employees Group Life Insurance (FEGLI)",
    entries=(
        SlotEntry(kind=SlotKind.GOVERNED, key="fegli.purpose",
                   label="FEGLI Purpose", positions=(BranchPosition(BRANCH_DEFAULT, 1),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="fegli.coverage_available",
                   label="FEGLI Coverage Available table", positions=(BranchPosition(BRANCH_DEFAULT, 2),),
                   description="Category B governed structural table"),
        SlotEntry(kind=SlotKind.GOVERNED, key="fegli.extra_benefit_under_45",
                   label="FEGLI Extra Benefit for Employees Under Age 45",
                   positions=(BranchPosition(BRANCH_DEFAULT, 3),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="fegli.adding_coverage",
                   label="Adding FEGLI Coverage", positions=(BranchPosition(BRANCH_DEFAULT, 4),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="fegli.open_seasons",
                   label="FEGLI Open Seasons", positions=(BranchPosition(BRANCH_DEFAULT, 5),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="fegli.postal_workers",
                   label="FEGLI Postal Workers note", positions=(BranchPosition(BRANCH_DEFAULT, 6),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="fegli.keeping_fegli_in_retirement",
                   label="Keeping FEGLI in Retirement", positions=(BranchPosition(BRANCH_DEFAULT, 7),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="fegli.choices_in_retirement",
                   label="FEGLI Choices in Retirement", positions=(BranchPosition(BRANCH_DEFAULT, 8),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="fegli.choices_in_retirement_table",
                   label="FEGLI Choices in Retirement table", positions=(BranchPosition(BRANCH_DEFAULT, 9),),
                   description="Category B governed structural table"),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="fegli.coverage_elected_intro_deferred",
            label="FEGLI Coverage Elected intro (deferred)",
            positions=(BranchPosition(BRANCH_DEFAULT, 10),),
            retirement_type=("Deferred",),
            description="Tie at position 10 with coverage_elected_intro_not_deferred",
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="fegli.coverage_elected_intro_not_deferred",
            label="FEGLI Coverage Elected intro (not deferred)",
            positions=(BranchPosition(BRANCH_DEFAULT, 10),),
            retirement_type=("Regular", "VERA / DSR"),
        ),
        SlotEntry(
            kind=SlotKind.COMPUTED,
            placeholder_id="computed:fegli.current_coverage_table",
            label="Current-coverage table (computed)",
            positions=(),
            anchor_after_variant_group=(
                "fegli.coverage_elected_intro_deferred",
                "fegli.coverage_elected_intro_not_deferred",
            ),
            description=(
                "Calculated per-case; not editable. CONFIRMED (Laravel Verification Section 6): a "
                "single, unconditional, non-duplicated table — same single table instance and position "
                "regardless of which of the two mutually exclusive narrative variants rendered. Anchored "
                "to the variant pair AS A WHOLE (anchor_after_variant_group), not to one individual "
                "variant, for the same reason as the Pension projection table above."
            ),
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="fegli.in_retirement_intro",
            label="FEGLI in Retirement intro",
            positions=(BranchPosition(BRANCH_DEFAULT, 11),),
            retirement_type=("Regular", "VERA / DSR"),
            description="Only rendered when retirementType != Deferred",
        ),
        SlotEntry(
            kind=SlotKind.COMPUTED,
            placeholder_id="computed:fegli.in_retirement_cost_coverage_matrix_table",
            label="FEGLI-in-retirement cost/coverage-choices matrix table (computed)",
            positions=(),
            anchor_after="fegli.in_retirement_intro",
            description="Calculated per-case; not editable; large multi-scenario matrix.",
        ),
    ),
)

# ---------------------------------------------------------------------------
# Section 6: fehb
# ---------------------------------------------------------------------------

_FEHB = ReportSection(
    group_key="fehb",
    section_label="Federal Employees Health Benefits (FEHB)",
    entries=(
        SlotEntry(kind=SlotKind.GOVERNED, key="fehb.purpose",
                   label="FEHB Purpose", positions=(BranchPosition(BRANCH_DEFAULT, 1),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="fehb.coverage_available",
                   label="FEHB Coverage Available", positions=(BranchPosition(BRANCH_DEFAULT, 2),),
                   description="Plain prose — not a table (unlike fegli.coverage_available)"),
        SlotEntry(kind=SlotKind.GOVERNED, key="fehb.taxes_on_premiums",
                   label="Taxes on FEHB Premiums", positions=(BranchPosition(BRANCH_DEFAULT, 3),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="fehb.eligibility_to_keep_in_retirement",
                   label="Eligibility to Keep FEHB in Retirement",
                   positions=(BranchPosition(BRANCH_DEFAULT, 4),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="fehb.dual_federal_couples",
                   label="Dual Federal Couples", positions=(BranchPosition(BRANCH_DEFAULT, 5),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="fehb.changes_in_retirement",
                   label="Changes to FEHB in Retirement", positions=(BranchPosition(BRANCH_DEFAULT, 6),),
                   description="New page follows this block (section banner re-renders mid-section)"),
        SlotEntry(kind=SlotKind.GOVERNED, key="fehb.current_cost_intro",
                   label="Current FEHB/Dental/Vision cost intro", positions=(BranchPosition(BRANCH_DEFAULT, 7),)),
        SlotEntry(
            kind=SlotKind.COMPUTED,
            placeholder_id="computed:fehb.current_cost_table",
            label="Current-cost table (computed)",
            positions=(),
            anchor_after="fehb.current_cost_intro",
            description="Calculated per-case; not editable.",
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="fehb.deferred_sentence",
            label="FEHB deferred-retiree termination sentence",
            positions=(BranchPosition(BRANCH_DEFAULT, 8),),
            retirement_type=("Deferred",),
            description="Tie at position 8 with projection_intro_not_deferred; no computed table follows "
                        "this deferred variant (consistent with 'coverage terminates' messaging)",
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="fehb.projection_intro_not_deferred",
            label="FEHB projection intro (not deferred)",
            positions=(BranchPosition(BRANCH_DEFAULT, 8),),
            retirement_type=("Regular", "VERA / DSR"),
        ),
        SlotEntry(
            kind=SlotKind.COMPUTED,
            placeholder_id="computed:fehb.multi_year_cost_projection_table",
            label="Multi-year FEHB cost projection table (computed)",
            positions=(),
            anchor_after="fehb.projection_intro_not_deferred",
            description="Calculated per-case; not editable; not present in the deferred path.",
        ),
    ),
)

# ---------------------------------------------------------------------------
# Section 7: fltcip (no ties)
# ---------------------------------------------------------------------------

_FLTCIP = ReportSection(
    group_key="fltcip",
    section_label="Federal Long Term Care Insurance Program (FLTCIP)",
    entries=(
        SlotEntry(kind=SlotKind.GOVERNED, key="fltcip.what_is_ltc",
                   label="What are Considered Long Term Care Services",
                   positions=(BranchPosition(BRANCH_DEFAULT, 1),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="fltcip.purpose",
                   label="Purpose of Long Term Care Insurance", positions=(BranchPosition(BRANCH_DEFAULT, 2),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="fltcip.cost_of_ltc_services",
                   label="Cost of Long Term Care Services", positions=(BranchPosition(BRANCH_DEFAULT, 3),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="fltcip.program_structure",
                   label="How the FLTCIP Program is Structured",
                   positions=(BranchPosition(BRANCH_DEFAULT, 4),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="fltcip.eligibility",
                   label="FLTCIP Eligibility", positions=(BranchPosition(BRANCH_DEFAULT, 5),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="fltcip.coverage_available_intro",
                   label="FLTCIP Coverage Available feature table",
                   positions=(BranchPosition(BRANCH_DEFAULT, 6),),
                   description="Category B governed structural table"),
        SlotEntry(kind=SlotKind.GOVERNED, key="fltcip.proof_of_insurability",
                   label="Proof of Insurability", positions=(BranchPosition(BRANCH_DEFAULT, 7),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="fltcip.state_partnership_plans",
                   label="State Partnership Plans", positions=(BranchPosition(BRANCH_DEFAULT, 8),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="fltcip.discounts",
                   label="FLTCIP Discounts", positions=(BranchPosition(BRANCH_DEFAULT, 9),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="fltcip.coverage_elected_intro",
                   label="FLTCIP Coverage Elected intro", positions=(BranchPosition(BRANCH_DEFAULT, 10),)),
        SlotEntry(
            kind=SlotKind.COMPUTED,
            placeholder_id="computed:fltcip.cost_projection_table",
            label="FLTCIP cost projection table (computed)",
            positions=(),
            anchor_after="fltcip.coverage_elected_intro",
            description="Calculated per-case; not editable.",
        ),
    ),
    unwired_keys=("fltcip.coverage_description",),
)

# ---------------------------------------------------------------------------
# Section 8: tsp (Thrift Savings Plan)
# ---------------------------------------------------------------------------

_TSP = ReportSection(
    group_key="tsp",
    section_label="Thrift Savings Plan (TSP)",
    entries=(
        SlotEntry(kind=SlotKind.GOVERNED, key="tsp.eligibility",
                   label="TSP Eligibility", positions=(BranchPosition(BRANCH_DEFAULT, 1),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="tsp.regular_contribution_limits",
                   label="TSP Regular Contribution Limits", positions=(BranchPosition(BRANCH_DEFAULT, 2),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="tsp.catchup_contribution_limits",
                   label="TSP Catch-up Contribution Limits", positions=(BranchPosition(BRANCH_DEFAULT, 3),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="tsp.agency_contributions_and_matching",
                   label="Agency Contributions & Matching Funds",
                   positions=(BranchPosition(BRANCH_DEFAULT, 4),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="tsp.tax_advantages_traditional",
                   label="TSP Tax Advantages - Traditional", positions=(BranchPosition(BRANCH_DEFAULT, 5),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="tsp.tax_advantages_roth",
                   label="TSP Tax Advantages - Roth", positions=(BranchPosition(BRANCH_DEFAULT, 6),),
                   description="Rendered immediately after tax_advantages_traditional with no separating heading"),
        SlotEntry(kind=SlotKind.GOVERNED, key="tsp.loans",
                   label="TSP Loans", positions=(BranchPosition(BRANCH_DEFAULT, 7),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="tsp.five_funds_available",
                   label="The 5 Funds Available table", positions=(BranchPosition(BRANCH_DEFAULT, 8),),
                   description="Category B governed structural table"),
        SlotEntry(kind=SlotKind.GOVERNED, key="tsp.new_contributions_intro",
                   label="New Contributions & Additions intro", positions=(BranchPosition(BRANCH_DEFAULT, 9),),
                   description="New page follows tsp.five_funds_available"),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="tsp.match_threshold_sentence",
            label="Matching Funds - at-threshold sentence",
            positions=(BranchPosition(BRANCH_DEFAULT, 10),),
            system_type=("FERS", "Transfers"),
            description="3-way tie at position 10 with agency_match_explanation and no_agency_match_csrs; "
                        "hit_full_tsp_match (>= 4.95%)",
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="tsp.agency_match_explanation",
            label="Matching Funds - below-threshold explanation",
            positions=(BranchPosition(BRANCH_DEFAULT, 10),),
            system_type=("FERS", "Transfers"),
            description="hit_full_tsp_match false (< 4.95%)",
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="tsp.no_agency_match_csrs",
            label="No Agency Match (CSRS)",
            positions=(BranchPosition(BRANCH_DEFAULT, 10),),
            system_type=("CSRS", "CSRS Offset"),
        ),
        SlotEntry(kind=SlotKind.GOVERNED, key="tsp.current_balance_growth_intro",
                   label="Current Balance & Growth intro", positions=(BranchPosition(BRANCH_DEFAULT, 11),)),
        SlotEntry(
            kind=SlotKind.COMPUTED,
            placeholder_id="computed:tsp.per_fund_balance_allocation_projection_table",
            label="Per-fund current-balance/allocation/projected-ending-balance table (computed)",
            positions=(),
            anchor_after="tsp.current_balance_growth_intro",
            description="Calculated per-case; not editable; covers 16 funds incl. L-funds.",
        ),
    ),
)

# ---------------------------------------------------------------------------
# Section 9: irs_penalty — entirely a 5-way tie
# ---------------------------------------------------------------------------
# VERIFIED (Phase 1 Reconciliation): the $irsPenaltyContentKey selection logic
# in benefits-software's EmployeeController@createPdfFEGLI (lines 1560-1629)
# was independently re-read in
# docs/PDF_CONTENT_EDITOR_PHASE1_LARAVEL_VERIFICATION.md Section 7. It is a
# clean, linear if/elseif/else chain, first match wins, with no re-entrant or
# overlapping conditions — "Selector found — not UNRESOLVED." This supersedes
# the original Phase 1 "not independently reverified" caveat for the five
# entries below. The five keys and their relative order were already
# correct in the original Phase 1 map; only the descriptions were expanded
# with the verified precedence/conditions.
#
# IRS_PENALTY_RENDERER_REGRESSION_RISK (see constant below, defined once and
# referenced here) documents a genuine, newly-found Benefits-Software-side
# regression-testing gap. Advisor Portal makes no code change in response to
# it — it is recorded purely as documentation for whoever owns Phase 2
# regression tooling, per this task's explicit instruction not to modify
# Benefits Software or its validation harness.

_IRS_PENALTY = ReportSection(
    group_key="irs_penalty",
    section_label="IRS Early Withdrawal Penalty",
    entries=(
        SlotEntry(
            kind=SlotKind.GOVERNED, key="irs_penalty.eligible_at_59_5",
            label="Already 59.5+ / penalty-free wording",
            positions=(BranchPosition(BRANCH_DEFAULT, 1),),
            description=(
                "Precedence 1 of 5 (first match wins; 5-way tie, exactly one renders). Verified "
                "condition (EmployeeController.php lines 1604-1605): "
                "(retirementAge == 59 AND retirementAge_month >= 6) OR retirementAge >= 60. "
                "See IRS_PENALTY_RENDERER_REGRESSION_RISK for an outstanding Benefits-Software-side "
                "regression-testing caveat that applies to all 5 keys in this tie."
            ),
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="irs_penalty.special_provision_meets_rules",
            label="Special Provision — meets age/service rules wording",
            positions=(BranchPosition(BRANCH_DEFAULT, 1),),
            description=(
                "Precedence 2 of 5. Verified condition (EmployeeController.php lines 1610-1612): "
                "isSpecialProvision (EmployeeType == 'Other' OR qualifying eCBPO/LEO date math, measured "
                "from a fixed 2008-07-06 LEO-eligibility start date) AND meetsSPRules "
                "(ageRetCalenderYear >= 50 OR coveredServiceYears >= 25, the latter measured from "
                "LeaveSCD to RetirementDate)."
            ),
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="irs_penalty.special_provision_not_meets_rules",
            label="Special Provision — does not meet rules wording",
            positions=(BranchPosition(BRANCH_DEFAULT, 1),),
            description=(
                "Precedence 3 of 5. Verified condition (EmployeeController.php line 1615): "
                "isSpecialProvision AND NOT meetsSPRules."
            ),
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="irs_penalty.regular_not_meets_age55",
            label="Regular employee — does not meet age 55 rule wording",
            positions=(BranchPosition(BRANCH_DEFAULT, 1),),
            description=(
                "Precedence 4 of 5. Verified condition (EmployeeController.php lines 1620-1621): "
                "NOT isSpecialProvision AND ageRetCalenderYear < 55."
            ),
        ),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="irs_penalty.regular_meets_age55",
            label="Regular employee — meets age 55 rule wording",
            positions=(BranchPosition(BRANCH_DEFAULT, 1),),
            description=(
                "Precedence 5 of 5. Verified condition (EmployeeController.php line 1624): "
                "NOT isSpecialProvision AND ageRetCalenderYear >= 55."
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# Section 10: checklist
# ---------------------------------------------------------------------------

_CHECKLIST = ReportSection(
    group_key="checklist",
    section_label="Checklist (Self-Assessment of Potential Action Items)",
    entries=(
        SlotEntry(kind=SlotKind.GOVERNED, key="checklist.intro",
                   label="Checklist intro paragraph", positions=(BranchPosition(BRANCH_DEFAULT, 1),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="checklist.mark_areas_prompt",
                   label="Mark the areas prompt", positions=(BranchPosition(BRANCH_DEFAULT, 2),)),
        SlotEntry(kind=SlotKind.GOVERNED, key="checklist.topics_before_srs",
                   label="Pre-SRS topic list (Pension/FERS; Survivor Benefit Plan)",
                   positions=(BranchPosition(BRANCH_DEFAULT, 3),)),
        SlotEntry(
            kind=SlotKind.GOVERNED, key="checklist.srs_topic",
            label="SRS/Social-Security topic list",
            positions=(BranchPosition(BRANCH_DEFAULT, 4),),
            system_type=("FERS", "Transfers"),
            description="Only renders for FERS/Transfers; CSRS/CSRS Offset skips directly from "
                        "topics_before_srs to topics_after_srs",
        ),
        SlotEntry(kind=SlotKind.GOVERNED, key="checklist.topics_after_srs",
                   label="Post-SRS topic list (TSP; FEGLI; FEHB; FLTCIP; General Concerns)",
                   positions=(BranchPosition(BRANCH_DEFAULT, 5),)),
    ),
    unwired_keys=("checklist.next_steps",),
)

# ---------------------------------------------------------------------------
# The complete map, in verified PDF section order (matches the real, local-DB
# confirmed ContentBlockGroup.display_order sequence — Local Database
# Verification Section 2).
# ---------------------------------------------------------------------------

PDF_STRUCTURE_MAP: Tuple[ReportSection, ...] = (
    _COVER,
    _PENSION,
    _SBP,
    _SRS_SS,
    _FEGLI,
    _FEHB,
    _FLTCIP,
    _TSP,
    _IRS_PENALTY,
    _CHECKLIST,
)

# ---------------------------------------------------------------------------
# Ungoverned sections — whole real PDF sections with no ContentBlockGroup at
# all. Never editable through this panel under any key.
# ---------------------------------------------------------------------------

_DISCLAIMER_RELEASE_BANNER_NOTE = (
    "PDF_CONTENT_ARCHITECTURE_AUDIT.md Section 4 verified (by reading "
    "report_pdf.blade.php's physical source) that a combined 'Disclaimer & "
    "\"Data Used in Preparation\"' banner area (~lines 281-420) renders after "
    "the Cover Page group (~lines 1-280) and before the Federal Pension group "
    "(~lines 421-730) — so placement in the cover-to-pension gap is evidence-"
    "based. The audit recorded this as ONE combined row, so the relative "
    "order between 'Disclaimer & Release' and 'Data Used in Preparation of "
    "This Report' as two distinct sections — and whether they are in fact two "
    "separate banners or one — is NOT independently established by that "
    "evidence. This is an explicit, documented ambiguity, not a resolved fact."
)

UNGOVERNED_SECTIONS: Tuple[UngovernedSection, ...] = (
    UngovernedSection(
        label="Disclaimer & Release",
        after_group="cover",
        before_group="pension",
        description=_DISCLAIMER_RELEASE_BANNER_NOTE,
    ),
    UngovernedSection(
        label="Data Used in Preparation of This Report",
        after_group="cover",
        before_group="pension",
        description=_DISCLAIMER_RELEASE_BANNER_NOTE,
    ),
)

# ---------------------------------------------------------------------------
# Inactive content records — real ContentBlock rows confirmed `is_active=False`
# in PDF_CONTENT_LOCAL_DATABASE_VERIFICATION.md Section 3.2. Never appear
# anywhere in PDF_STRUCTURE_MAP above (neither as a GOVERNED entry nor as an
# unwired key) — they are excluded from the report outline entirely, not
# merely marked.
# ---------------------------------------------------------------------------

INACTIVE_BLOCK_KEYS = frozenset({
    "fegli.basic_description",
})

# ---------------------------------------------------------------------------
# Keys intentionally occupying more than one BranchPosition (genuine reuse at
# different physical positions, not a transcription duplicate). See module
# docstring "Deviations" item 1 for why this has 4 members, not the 5 the
# design document anticipated.
# ---------------------------------------------------------------------------

REPEATED_KEY_ALLOWLIST = frozenset({
    "srs_ss.ss_eligibility",
    "srs_ss.ss_earnings_test",
    "srs_ss.ss_cola",
    "srs_ss.wep_paragraph",
})

# ---------------------------------------------------------------------------
# Phase 1 Reconciliation additions
# ---------------------------------------------------------------------------

# Keys whose literal "Verified PDF Order (within group)" position NUMBER in
# PDF_CONTENT_BLOCK_INVENTORY.csv is known to be superseded by the stronger,
# more direct evidence in
# docs/PDF_CONTENT_EDITOR_PHASE1_LARAVEL_VERIFICATION.md. The CSV's numbering
# for these four keys conflated a per-branch count with a separate shared-
# paragraph count (see the `srs_ss` section's BRANCH_SHARED entries above);
# the Laravel verification is authoritative for these specific rendering
# behaviors, per this phase's instructions. Used only to narrow the scope of
# the CSV cross-check test — it does not affect the map's own correctness.
CSV_POSITION_SUPERSEDED_BY_LARAVEL_VERIFICATION = frozenset({
    "srs_ss.summary_deferred_note",
    "srs_ss.summary_earnings_test_note",
    "srs_ss.summary_ss_note",
    "srs_ss.wep_sentence",
})

# A genuine, newly-found Benefits-Software-side regression-testing risk
# (docs/PDF_CONTENT_EDITOR_PHASE1_LARAVEL_VERIFICATION.md Sections 1.7 and
# 7-8). Recorded here as documentation only, per this phase's explicit
# instruction not to modify Benefits Software or its validation harness, and
# not to introduce new business-rule evaluation into Advisor Portal — this
# constant is inert text, never evaluated by any function in this module.
IRS_PENALTY_RENDERER_REGRESSION_RISK = (
    "benefits-software's FactFinderReportRenderer::renderHtml() (the golden-master/"
    "validation harness renderer, not the production controller) independently "
    "reimplements the same 5-way IRS-penalty precedence logic in a private "
    "buildIrsPenaltyText() method, but never computes or passes an "
    "irsPenaltyContentKey to the Blade view. Because the template falls back to "
    "$irsPenaltyContentKey ?? '', any report rendered through this harness path can "
    "never resolve a governed-content override for irs_penalty.* keys, even though "
    "its computed fallback TEXT matches the production controller's text exactly. "
    "This does not affect the real, production PDF (EmployeeController@createPdfFEGLI "
    "does set the key) but it DOES mean a Phase 2 regression/golden-master suite built "
    "on FactFinderReportRenderer would silently fail to catch irs_penalty.* governed-"
    "content regressions. Outstanding risk for whoever owns Phase 2 regression tooling "
    "— not an Advisor Portal defect, and not corrected here (no Benefits Software or "
    "Laravel file may be modified under this phase's authorization)."
)


def _branch_for_system_type(system_type):
    """Return which per-system-type BranchPosition scope a given real
    `system_type` value resolves to, for `resolve_outline()` below. Pure
    lookup table — not a rule engine, not a business calculation."""
    if system_type in ("FERS", "Transfers"):
        return BRANCH_FERS_TRANSFERS
    if system_type in ("CSRS", "CSRS Offset"):
        return BRANCH_CSRS_CSRS_OFFSET
    raise ValueError(f"Unknown system_type {system_type!r}; expected one of {SYSTEM_TYPES}")


def resolve_outline(group_key, system_type, retirement_type=None):
    """Return the ordered list of GOVERNED `SlotEntry` objects that would
    appear in `group_key`'s presentation outline for a given
    (system_type, retirement_type) scenario.

    This is a small, deterministic, read-only, presentation-only helper over
    this module's own static data — it exists so a future editor (or a test)
    can ask "what would a FERS retiree see, in order" without hand-coding the
    branch/shared-scope logic itself. It:

    - Filters out any entry/occurrence whose documented `system_type`/
      `retirement_type` condition excludes the given scenario (an entry
      with `system_type=None` is unrestricted and always included; same for
      `retirement_type=None`). A `BranchPosition.system_type` override, when
      set, applies to just that one occurrence instead of the entry's own
      `system_type` — needed for keys like `srs_ss.wep_paragraph` whose real
      condition genuinely differs by branch.
    - Orders branch-specific source occurrences (the real per-system-type
      BranchPosition, e.g. BRANCH_FERS_TRANSFERS or BRANCH_CSRS_CSRS_OFFSET
      for `srs_ss`, or BRANCH_DEFAULT for every other group) before any
      BRANCH_SHARED occurrences, matching the verified real-source fact that
      shared content is reached only after branch-specific content closes.
      Entries at the same logical position retain their declaration order,
      which records precedence for same-slot alternatives such as IRS and TSP.
    - When `retirement_type` is omitted, does NOT collapse retirement-type
      ties (e.g. deferred vs. not-deferred) — both members of such a tie are
      returned, since the scenario is under-specified to pick one.

    It does NOT evaluate `ContentBlock.display_condition`, does not read any
    live Fact Finder Data Contract data, and performs no business
    calculation — it only sorts/filters this module's own declared
    annotations.
    """
    if system_type not in SYSTEM_TYPES:
        raise ValueError(f"Unknown system_type {system_type!r}; expected one of {SYSTEM_TYPES}")
    if retirement_type is not None and retirement_type not in RETIREMENT_TYPES:
        raise ValueError(f"Unknown retirement_type {retirement_type!r}; expected one of {RETIREMENT_TYPES}")

    section = next((s for s in PDF_STRUCTURE_MAP if s.group_key == group_key), None)
    if section is None:
        raise ValueError(f"Unknown group_key {group_key!r}")

    if group_key == "srs_ss":
        branch_scopes = {_branch_for_system_type(system_type): 0, BRANCH_SHARED: 1}
    else:
        branch_scopes = {BRANCH_DEFAULT: 0}

    matches = []
    for declaration_order, entry in enumerate(section.entries):
        if entry.kind is not SlotKind.GOVERNED:
            continue
        if retirement_type is not None and entry.retirement_type is not None \
                and retirement_type not in entry.retirement_type:
            continue
        for bp in entry.positions:
            if bp.branch not in branch_scopes:
                continue
            effective_system_type = bp.system_type if bp.system_type is not None else entry.system_type
            if effective_system_type is not None and system_type not in effective_system_type:
                continue
            matches.append((branch_scopes[bp.branch], bp.position, declaration_order, entry))

    matches.sort(key=lambda item: (item[0], item[1], item[2]))
    return [entry for *_sort_key, entry in matches]


# ---------------------------------------------------------------------------
# Read-only helper functions
# ---------------------------------------------------------------------------

def governed_entries(sections=None):
    """Yield (ReportSection, SlotEntry) for every GOVERNED entry in `sections`
    (defaults to the real PDF_STRUCTURE_MAP). The optional parameter exists
    only so tests can exercise this logic against a small, hand-built fake
    structure without mutating the real, frozen module data."""
    for section in (PDF_STRUCTURE_MAP if sections is None else sections):
        for entry in section.entries:
            if entry.kind is SlotKind.GOVERNED:
                yield section, entry


def computed_entries(sections=None):
    """Yield (ReportSection, SlotEntry) for every COMPUTED entry in `sections`
    (defaults to the real PDF_STRUCTURE_MAP)."""
    for section in (PDF_STRUCTURE_MAP if sections is None else sections):
        for entry in section.entries:
            if entry.kind is SlotKind.COMPUTED:
                yield section, entry


def flatten_governed_keys(sections=None):
    """Return {ContentBlock.key: (ReportSection, SlotEntry)} for every
    GOVERNED entry. Raises ValueError if any key appears in more than one
    ReportSection (a real authoring error — never expected)."""
    flattened = {}
    for section, entry in governed_entries(sections):
        if entry.key in flattened:
            raise ValueError(f"Key {entry.key!r} appears in more than one ReportSection")
        flattened[entry.key] = (section, entry)
    return flattened


def dual_position_keys(sections=None):
    """Return the set of GOVERNED keys that carry more than one BranchPosition."""
    return {
        entry.key
        for _section, entry in governed_entries(sections)
        if len(entry.positions) > 1
    }


def variant_tie_groups(sections=None):
    """Return {(group_key, branch, position): [SlotEntry, ...]} restricted to
    groups with 2+ members — the mutually-exclusive narrative variant ties."""
    ties = {}
    for section, entry in governed_entries(sections):
        for bp in entry.positions:
            ties.setdefault((section.group_key, bp.branch, bp.position), []).append(entry)
    return {slot: members for slot, members in ties.items() if len(members) > 1}


def unwired_keys_by_group():
    """Return {group_key: tuple(unwired ContentBlock.key, ...)} for every
    ReportSection with a non-empty unwired_keys tuple."""
    return {
        section.group_key: section.unwired_keys
        for section in PDF_STRUCTURE_MAP
        if section.unwired_keys
    }


def all_unwired_keys():
    """Return the flat set of every active-but-unwired ContentBlock.key
    recorded across all ReportSections."""
    result = set()
    for keys in unwired_keys_by_group().values():
        result.update(keys)
    return result


def group_keys():
    """Return the tuple of all 10 governed ContentBlockGroup.key values, in
    verified PDF order."""
    return tuple(section.group_key for section in PDF_STRUCTURE_MAP)


def _validate():
    """Fail fast at import time on internal authoring mistakes. This does
    NOT verify this module against report_pdf.blade.php (no access to
    benefits-software in this phase) — only internal self-consistency."""
    flattened = flatten_governed_keys()

    governed_key_set = set(flattened)
    if governed_key_set != set(WIRED_BLOCK_KEYS):
        missing = set(WIRED_BLOCK_KEYS) - governed_key_set
        extra = governed_key_set - set(WIRED_BLOCK_KEYS)
        raise ValueError(
            f"PDF_STRUCTURE_MAP does not match WIRED_BLOCK_KEYS. "
            f"Missing from map: {sorted(missing)}. Unexpected in map: {sorted(extra)}."
        )

    if dual_position_keys() != REPEATED_KEY_ALLOWLIST:
        raise ValueError(
            f"Dual-position keys {sorted(dual_position_keys())} do not match "
            f"REPEATED_KEY_ALLOWLIST {sorted(REPEATED_KEY_ALLOWLIST)}."
        )

    for (group_key_, _branch, _position), members in variant_tie_groups().items():
        for member in members:
            if not (member.system_type or member.retirement_type or member.description):
                raise ValueError(
                    f"Tied entry {member.key!r} in group {group_key_!r} has no "
                    "system_type, retirement_type, or description explaining its condition."
                )

    for section, entry in computed_entries():
        anchor_keys = {e.key for e in section.entries if e.kind is SlotKind.GOVERNED}
        if entry.anchor_after is not None:
            if entry.anchor_after not in anchor_keys:
                raise ValueError(
                    f"Computed placeholder {entry.placeholder_id!r} anchors to "
                    f"{entry.anchor_after!r}, which is not a governed key in its own section."
                )
        if entry.anchor_after_variant_group is not None:
            missing_anchors = set(entry.anchor_after_variant_group) - anchor_keys
            if missing_anchors:
                raise ValueError(
                    f"Computed placeholder {entry.placeholder_id!r} anchors to variant group "
                    f"{entry.anchor_after_variant_group!r}, which contains keys not governed in its "
                    f"own section: {sorted(missing_anchors)}."
                )

    for _section, entry in governed_entries():
        for bp in entry.positions:
            if bp.branch not in (BRANCH_DEFAULT, BRANCH_FERS_TRANSFERS, BRANCH_CSRS_CSRS_OFFSET, BRANCH_SHARED):
                raise ValueError(f"{entry.key!r} uses an unknown branch {bp.branch!r}.")

    placeholder_ids = [entry.placeholder_id for _s, entry in computed_entries()]
    if len(placeholder_ids) != len(set(placeholder_ids)):
        raise ValueError("Duplicate COMPUTED placeholder_id values found.")

    if governed_key_set & INACTIVE_BLOCK_KEYS:
        raise ValueError("An inactive key must not appear as a GOVERNED entry.")

    if governed_key_set & all_unwired_keys():
        raise ValueError("An unwired key must not appear as a GOVERNED entry.")

    if INACTIVE_BLOCK_KEYS & all_unwired_keys():
        raise ValueError("Inactive and unwired key registries must be disjoint.")


_validate()
