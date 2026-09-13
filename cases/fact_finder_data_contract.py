"""
Fact Finder Data Contract (schema v1 / "2026.1")

NOT the same thing as `FederalFactFinder` (see cases/models_fact_finder.py), which is the
advisor-facing INTAKE form (the official ProFeds "Federal Fact Finder" questionnaire PDF
that advisors fill out and upload). The two happen to share the name "Fact Finder" because
they're both part of the same domain, but they are unrelated data structures.

This module defines the OUTPUT contract described in
docs/FACT_FINDER_PDF_MODERNIZATION_ANALYSIS_2026-09-06.md: a versioned, computed-only
structure that `benefits-software`'s calculation engine (EmployeeRepository.php) should
eventually emit, and that any Fact Finder PDF renderer (the existing TCPDF/Blade template,
or a future renderer) should only ever consume, never recompute.

Field names below are grounded in verified return shapes read directly from
`benefits-software/app/Repositories/EmployeeRepository.php` and
`benefits-software/app/Http/Controllers/Admin/EmployeeController.php` — not guessed.
Where a field does not exist yet in the current PHP code (everything under
`computed_flags`), that is called out explicitly; producing those flags is Phase 2 work,
not this file.

Phase 1 scope only: this is a schema definition + validation. It is not wired into any
view, API endpoint, or production code path yet. No data flows through it.
"""
from rest_framework import serializers

SCHEMA_VERSION = "2026.1"


class PensionScenarioSerializer(serializers.Serializer):
    """One of the 6 pre-calculated retirement scenarios.

    Grounded in EmployeeRepository::getFirstPension($empId, $scenario),
    ::getMRAPenalty(), ::getEarlyOutPenalty(), ::getCsrsOffsetPenalty() (all take a
    $scenario argument of 1-6).
    """
    scenario_number = serializers.IntegerField(min_value=1, max_value=6)
    retirement_date = serializers.DateField(required=False, allow_null=True)
    gross_annual_pension = serializers.DecimalField(max_digits=12, decimal_places=2)
    first_pension_mra10_penalty = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    months_under_62 = serializers.IntegerField(required=False, allow_null=True)
    multiplier = serializers.DecimalField(max_digits=6, decimal_places=4, required=False, allow_null=True)
    early_out_penalty = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    csrs_offset_penalty = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)


class PensionSerializer(serializers.Serializer):
    scenarios = PensionScenarioSerializer(many=True)
    non_deduction_penalty = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    refunded_penalty = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    wep_penalty = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    mra_year = serializers.IntegerField(
        required=False, allow_null=True,
        help_text=(
            "Grounded in EmployeeRepository::getMinumumRetirementAge($empId)['mra_year'] "
            "(note: 'Minumum' typo preserved verbatim from the real PHP method name) — the "
            "whole-years component of a FERS employee's Minimum Retirement Age, used in "
            "report_pdf.blade.php's MRA paragraph: '{{ $minimumRetirementAge['mra_year'] }}y "
            "{{ $minimumRetirementAge['mra_month'] }}m'. Null when DateOfBirth is missing "
            "(the PHP method returns '' in that case; the builder coerces '' to null)."
        ),
    )
    mra_month = serializers.IntegerField(
        required=False, allow_null=True,
        help_text="The months component of MRA, alongside mra_year above — same source method.",
    )
    cola = serializers.DecimalField(
        max_digits=6, decimal_places=3, required=False, allow_null=True,
        help_text=(
            "Grounded in EmployeeRepository::getPensionDetailsPdf()['cola'] — the system-type-"
            "specific 10-year average COLA percentage ($empConf['FERSCola'] or "
            "$empConf['CSRSCola']). Used as a merge field in report_pdf.blade.php's pension "
            "narrative: '...A Cost of Living Adjustment (COLA) has been applied to your pension "
            "...(the 10-year average is {{$pension['cola']}}%).'"
        ),
    )
    retirement_date = serializers.CharField(
        required=False, allow_null=True,
        help_text=(
            "Grounded in EmployeeRepository::getPensionDetailsPdf()['retirement_date'] — the "
            "employee's planned RetirementDate, PRE-FORMATTED as 'm/d/Y' (e.g. '12/31/2026') by "
            "the PHP source itself, not an ISO date. Deliberately a CharField (not DateField): "
            "this value's only real use is direct merge-field substitution into "
            "report_pdf.blade.php prose ('...on the date you planned "
            "({{ $pension['retirement_date'] }})...'), so it must carry the exact display string "
            "PHP already produces, not be reparsed/reformatted. NOT the same field as "
            "pension.scenarios[i].retirement_date above (a real per-scenario ISO DateField) — "
            "this is a single top-level, already-formatted display value for the primary scenario."
        ),
    )
    retirement_month_year = serializers.CharField(
        required=False, allow_null=True,
        help_text=(
            "Pre-formatted 'F Y' display string (e.g. 'December 2026'), derived from the same "
            "underlying RetirementDate as `retirement_date` above. Grounded in "
            "report_pdf.blade.php's 'Planned & Delayed Retirement' intro paragraph: "
            "\"...you plan to retire in {{date('F Y', strtotime($pension['retirement_date']))}}...\" "
            "— note the template itself re-parses the already-formatted `retirement_date` string "
            "rather than a raw date; this field reproduces that exact formatting faithfully."
        ),
    )
    retirement_age_years = serializers.IntegerField(
        required=False, allow_null=True,
        help_text="Grounded in EmployeeRepository::getPensionDetailsPdf()['retirementAgeY'].",
    )
    retirement_age_months = serializers.IntegerField(
        required=False, allow_null=True,
        help_text="Grounded in EmployeeRepository::getPensionDetailsPdf()['retirementAgeM'].",
    )
    unused_sick_leave_hours = serializers.IntegerField(
        required=False, allow_null=True,
        help_text=(
            "Grounded in $pdf_data['employee']['UnusedSickLeave'], rounded to the nearest whole "
            "hour — matches report_pdf.blade.php's 'Planned & Delayed Retirement' paragraph: "
            "'{{round($pdf_data['employee']['UnusedSickLeave'])}} hours'."
        ),
    )
    unused_sick_leave_months = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True,
        help_text=(
            "The federal 2,087-hours-per-year conversion of unused_sick_leave_hours into months "
            "(hours / 2087 * 12), rounded to 2 decimal places. GENUINELY NEW computed field, "
            "added 2026-09-13 with explicit user approval — this conversion previously existed "
            "ONLY inline in report_pdf.blade.php, nowhere in EmployeeRepository, unlike every "
            "other Data Contract field which is a pure reshaping of an already-computed PHP "
            "value. Grounded in the exact same 2,087-hour/year rule already explained in the "
            "'Applying Unused Sick Leave' paragraph migrated earlier (see the OPM '2,087 chart')."
        ),
    )


class FegliCurrentElectionsSerializer(serializers.Serializer):
    """Grounded in EmployeeRepository::getFegliReport()'s `current_fegli` key."""
    basic = serializers.BooleanField()
    optionA = serializers.BooleanField()
    optionB = serializers.IntegerField(min_value=0)
    optionC = serializers.IntegerField(min_value=0)
    optionC_spouse = serializers.BooleanField(required=False)
    optionC_dependent = serializers.BooleanField(required=False)


class FegliProjectionRowSerializer(serializers.Serializer):
    """One row of `fegli_arr`, returned by EmployeeRepository::getFegliReport()."""
    age = serializers.IntegerField()
    years_in_retirement = serializers.CharField(
        help_text=(
            "Grounded in a real-data finding (2026-09-12 end-to-end validation, case #42293): "
            "this is NOT always numeric — getFegliReport() emits a literal '*' marker for at "
            "least one row (a footnote-style flag in the source table), so this must accept "
            "that value faithfully rather than force it into an IntegerField. CharField "
            "accepts int/float/bool-safe input too (DRF coerces via str()), so ordinary numeric "
            "rows still round-trip fine."
        )
    )
    annual_sal = serializers.DecimalField(max_digits=12, decimal_places=2)
    basic_coverage = serializers.DecimalField(max_digits=12, decimal_places=2)
    optionA_coverage = serializers.DecimalField(max_digits=12, decimal_places=2)
    optionB_coverage = serializers.DecimalField(max_digits=12, decimal_places=2)
    optionC_coverage = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_coverage = serializers.DecimalField(max_digits=12, decimal_places=2)
    totalBiWeekly = serializers.DecimalField(max_digits=12, decimal_places=2)
    totalMonthly = serializers.DecimalField(max_digits=12, decimal_places=2)
    totalYearly = serializers.DecimalField(max_digits=12, decimal_places=2)
    runningTotalCost = serializers.DecimalField(max_digits=12, decimal_places=2)


class FegliAllScenariosRowSerializer(serializers.Serializer):
    """One row from EmployeeRepository::getFegliAllScenarios() — the FEGLI election-combo
    projections shown in the "all scenarios" table."""
    age = serializers.IntegerField()
    basicCoverageNoReduction = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    basicCoverage50Reduction = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    basicCoverage75Reduction = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    basicCostNoReduction = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    basicCost50Reduction = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    basicCost75Reduction = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    optionACoverage = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    OptionACost = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    optionBCoverageNoReduction = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    OptionBCostNoReduction = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    optionBCoverageFullReduction = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    OptionBCostFullReduction = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    optionCCoverageNoReduction = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    optionCCostNoReduction = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    optionCCoverageFullReduction = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    optionCCostFullReduction = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)


class FegliSerializer(serializers.Serializer):
    current_fegli = FegliCurrentElectionsSerializer()
    is_married = serializers.BooleanField()
    has_dependents = serializers.BooleanField()
    fegli_arr = FegliProjectionRowSerializer(many=True)
    fegli_all_scenarios = FegliAllScenariosRowSerializer(many=True, required=False)


class SocialSecurityDetailRowSerializer(serializers.Serializer):
    """One row of `ss_details`, returned by EmployeeRepository::getSocialSecurityDetailPdf()."""
    years_in_ret = serializers.IntegerField()
    age = serializers.IntegerField()
    monthly_pension = serializers.DecimalField(max_digits=12, decimal_places=2)
    fers_srs = serializers.DecimalField(max_digits=12, decimal_places=2)
    ss_benefits = serializers.DecimalField(max_digits=12, decimal_places=2)
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    configInc = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)


class SocialSecuritySerializer(serializers.Serializer):
    ss_cola = serializers.DecimalField(max_digits=6, decimal_places=3)
    ss_earned_income_limit = serializers.DecimalField(max_digits=12, decimal_places=2)
    ss_details = SocialSecurityDetailRowSerializer(many=True)
    ss_years_earning = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text=(
            "Grounded in $pdf_data['employee']['SSYearsEarning'] — the input the WEP "
            "condition (< 30) is evaluated against in report_pdf.blade.php."
        ),
    )


class TspFundSerializer(serializers.Serializer):
    """One fund row. Deliberately a list (not one-column-per-fund) — see the analysis
    doc's TSP pain-point deep-dive on why per-fund columns (`GFund`, `L2050`, ...) don't
    scale when a new fund is added. `fund_code` values are grounded in the Tsp model's
    $fillable list (GFund/FFund/CFund/SFund/IFund/LIncome/L2020/L2030/L2040/L2050/...)."""
    fund_code = serializers.CharField()
    balance = serializers.DecimalField(max_digits=14, decimal_places=2)
    allocation_pct = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)


class TspSerializer(serializers.Serializer):
    """Grounded in EmployeeRepository::calcProjectedEndingBalanceTsp()."""
    funds = TspFundSerializer(many=True)
    agency_percentage = serializers.DecimalField(max_digits=6, decimal_places=3, required=False)
    agency_contribution = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    employee_contribution = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    sal_percentage_in_contri = serializers.DecimalField(max_digits=6, decimal_places=3)
    max_agency_contribution = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    # Added 2026-09-13 to support the TSP section's merge fields — all pure passthroughs of
    # values already computed by EmployeeRepository::getEmpTspConfigurations() /
    # calcProjectedEndingBalanceTsp(), grounded directly in report_pdf.blade.php's usage.
    year_of_contribution = serializers.IntegerField(required=False, allow_null=True)
    deff_limit = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    catchup_limit = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    gfund_rate = serializers.DecimalField(max_digits=6, decimal_places=3, required=False, allow_null=True)
    ffund_rate = serializers.DecimalField(max_digits=6, decimal_places=3, required=False, allow_null=True)
    cfund_rate = serializers.DecimalField(max_digits=6, decimal_places=3, required=False, allow_null=True)
    sfund_rate = serializers.DecimalField(max_digits=6, decimal_places=3, required=False, allow_null=True)
    ifund_rate = serializers.DecimalField(max_digits=6, decimal_places=3, required=False, allow_null=True)
    missing_out_amount = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    emp_min_contri_for_full_agency_contri = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    # ^ Both of the above are CharField, not DecimalField, because EmployeeRepository::
    # calcProjectedEndingBalanceTsp() returns them ALREADY pre-formatted via PHP's
    # number_format(round(...)) (e.g. "1,234" with a thousands separator) — passed straight
    # through to the merge field with no further formatting in Blade. A DecimalField would
    # reject that comma on any real value >= 1000.
    # A whole-number reformat of sal_percentage_in_contri (Blade calls round() with no
    # decimals specifically for the two Matching Funds sentences) — not a new calculation.
    sal_percentage_in_contri_rounded = serializers.IntegerField(required=False, allow_null=True)



class FehbSerializer(serializers.Serializer):
    """Grounded in $pdf_data['empConf']['FEHBAveragePremiumIncrease'] — the FEHB "in
    retirement" projection paragraph's 10-year-average cost-increase merge field. PHP
    falls back to the literal 4.83 when the per-employee config value is missing
    (`$pdf_data['empConf']['FEHBAveragePremiumIncrease'] ?? '4.83'`); the builder
    applies that same fallback, so this field is effectively never null in practice,
    but it's still required=False/allow_null=True for consistency with every other
    passthrough field and to tolerate older fixtures captured before this field existed.
    """
    average_premium_increase = serializers.DecimalField(
        max_digits=6, decimal_places=3, required=False, allow_null=True,
    )


class FltcipSerializer(serializers.Serializer):
    """Grounded in $pdf_data['empConf'][...] — the FLTCIP "Coverage available" table's
    4 merge fields. Unlike every other passthrough field so far, these are all STRING
    values (not numeric) — each one is a literal, human-readable description ('$100-
    $450/day', '2, 3, 5 years', etc.), not a computed figure. PHP falls back to a
    literal default string when the per-employee config value is missing; the builder
    applies those same defaults, so these fields are effectively never null in
    practice, but they're still required=False/allow_null=True for consistency with
    every other passthrough field and to tolerate older fixtures captured before FLTCIP
    was migrated.
    """
    daily_benefit_amount = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    benefit_period = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    waiting_period = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    inflation_protection = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class SystemSerializer(serializers.Serializer):
    SYSTEM_TYPE_CHOICES = ["FERS", "CSRS", "CSRS Offset", "Transfers"]
    # Verified 2026-09-13 directly against benefits-software's real RetirementType
    # lookup table (`AppLookup::where('AppLookupTypeName', 'RetirementType')`) —
    # these are the ONLY 3 values that exist in that table; there is no separate
    # "Optional" or "Disability" retirement type in this application at all. The
    # previous list (["Regular", "Optional", "Deferred", "Disability"]) was never
    # grounded in real data and caused every real VERA/early-out case (stored as
    # the literal string "VERA / DSR") to fail schema validation. Caught via the
    # golden-master pre-publish validation gate's 24 real-case fixtures.
    RETIREMENT_TYPE_CHOICES = ["Regular", "VERA / DSR", "Deferred"]

    system_type = serializers.ChoiceField(choices=SYSTEM_TYPE_CHOICES)
    retirement_type = serializers.ChoiceField(choices=RETIREMENT_TYPE_CHOICES)
    birth_year = serializers.IntegerField()
    current_year = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text=(
            "The calendar year date('Y') returns in report_pdf.blade.php today (e.g. the SRS/SS "
            "Earnings Test paragraphs' 'which for {{date('Y')}}...' wording). Derived from the "
            "same generated_at timestamp the contract already carries — not a new calculation."
        ),
    )


class ComputedFlagsSerializer(serializers.Serializer):
    """
    The key new piece this whole project is about: booleans the calculation layer
    already has enough information to produce, but does not currently expose — the PDF
    template re-derives them instead (see the analysis doc's Blade template deep-dive).

    None of these fields exist yet in benefits-software's output today. Phase 2 adds a
    single read-only aggregation method that derives them from values already returned
    by the methods referenced above — no new math, no changed calculations.

    Every flag below is traced to a specific `@if`/`@elseif` in report_pdf.blade.php,
    cataloged in benefits-software/PDF_USER_LITERAL_AND_CONDITIONAL_LOGIC.md — nothing
    here is speculative.
    """
    is_fers_or_transfers = serializers.BooleanField(
        help_text="systemType in ('FERS', 'Transfers') — drives pension/SBP/SRS/TSP-match wording branches."
    )
    is_csrs_or_csrs_offset = serializers.BooleanField(
        help_text="systemType in ('CSRS', 'CSRS Offset') — the explicit @elseif branch in the same sections "
        "(not just the logical negation of is_fers_or_transfers, since the template checks it directly)."
    )
    is_deferred_retirement = serializers.BooleanField(
        help_text="retirementType == 'Deferred' — drives pension/SBP/SRS/FEGLI/FEHB deferred-vs-immediate wording."
    )
    is_wep_applicable = serializers.BooleanField(
        help_text="(systemType in ('CSRS', 'CSRS Offset')) and (SSYearsEarning < 30) — today this exact "
        "compound condition is inline in the blade template's WEP sentence."
    )
    is_gpo_applicable = serializers.BooleanField(
        help_text="systemType == 'CSRS' (pure CSRS only, NOT CSRS Offset) — Government Pension Offset "
        "applies to the Social Security spousal benefit only for pure CSRS retirees."
    )
    hit_full_tsp_match = serializers.BooleanField(
        help_text=(
            "True when sal_percentage_in_contri >= 4.95. Today this threshold is "
            "hardcoded inline in resources/views/admin/employee/report_pdf.blade.php "
            "around line 2191 instead of being a precomputed flag."
        )
    )


class FactFinderDataContractSerializer(serializers.Serializer):
    """Top-level Fact Finder Data Contract, schema_version 2026.1."""
    schema_version = serializers.CharField(default=SCHEMA_VERSION)
    employee_id = serializers.IntegerField()
    generated_at = serializers.DateTimeField()
    system = SystemSerializer()
    pension = PensionSerializer()
    fegli = FegliSerializer()
    social_security = SocialSecuritySerializer()
    tsp = TspSerializer()
    fehb = FehbSerializer(required=False)
    fltcip = FltcipSerializer(required=False)
    computed_flags = ComputedFlagsSerializer()

    def validate_schema_version(self, value):
        if value != SCHEMA_VERSION:
            raise serializers.ValidationError(
                f"Unsupported schema_version '{value}'; this validator only accepts '{SCHEMA_VERSION}'."
            )
        return value
