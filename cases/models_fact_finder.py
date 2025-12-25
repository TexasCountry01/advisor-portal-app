"""
Federal Fact Finder Data Model
Comprehensive structure matching the official ProFeds Federal Fact Finder form
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class FederalFactFinder(models.Model):
    """
    Complete Federal Fact Finder form data - matches official ProFeds FFF rev 1-2025
    One-to-One relationship with Case for historical tracking and multi-dashboard access
    """
    
    # Relationship to Case
    case = models.OneToOneField(
        'Case',
        on_delete=models.CASCADE,
        related_name='fact_finder',
        primary_key=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # ========================================================================
    # PAGE 1: BASIC INFORMATION
    # ========================================================================
    
    # Employee Information
    employee_name = models.CharField(max_length=200, blank=True)
    employee_dob = models.DateField(null=True, blank=True, verbose_name="Employee Date of Birth")
    
    # Spouse Information
    spouse_name = models.CharField(max_length=200, blank=True)
    spouse_fed_emp = models.BooleanField(null=True, blank=True, verbose_name="Spouse is Federal Employee")
    spouse_dob = models.DateField(null=True, blank=True, verbose_name="Spouse Date of Birth")
    
    # Address
    address = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=2, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)
    
    # ========================================================================
    # RETIREMENT SYSTEM
    # ========================================================================
    
    RETIREMENT_SYSTEM_CHOICES = [
        ('CSRS', 'CSRS'),
        ('CSRS_OFFSET', 'CSRS Offset'),
        ('FERS', 'FERS'),
        ('FERS_TRANSFER', 'FERS Transfer'),
    ]
    
    retirement_system = models.CharField(max_length=20, choices=RETIREMENT_SYSTEM_CHOICES, blank=True)
    csrs_offset_date = models.DateField(null=True, blank=True, verbose_name="CSRS Offset Date")
    fers_transfer_date = models.DateField(null=True, blank=True, verbose_name="FERS Transfer Date")
    
    # ========================================================================
    # EMPLOYEE TYPE
    # ========================================================================
    
    EMPLOYEE_TYPE_CHOICES = [
        ('REGULAR', 'Regular'),
        ('POSTAL', 'Regular - Postal Worker'),
        ('MILITARY_TECH', 'Regular - Military Reserve Technician'),
        ('LEO', 'Law Enforcement'),
        ('CBPO', 'Customs & Border Protection Officer'),
        ('FIREFIGHTER', 'Firefighter'),
        ('ATC', 'Air Traffic Controller'),
        ('FOREIGN_SERVICE', 'Foreign Service'),
    ]
    
    employee_type = models.CharField(max_length=20, choices=EMPLOYEE_TYPE_CHOICES, blank=True)
    leo_start_date = models.DateField(null=True, blank=True, verbose_name="LEO Start Date")
    cbpo_on_date_7_6_2008 = models.BooleanField(null=True, blank=True, verbose_name="CBPO on 7/6/2008")
    firefighter_start_date = models.DateField(null=True, blank=True, verbose_name="Firefighter Start Date")
    atc_start_date = models.DateField(null=True, blank=True, verbose_name="ATC Start Date")
    foreign_service_start_date = models.DateField(null=True, blank=True, verbose_name="Foreign Service Start Date")
    
    # ========================================================================
    # RETIREMENT TYPE
    # ========================================================================
    
    RETIREMENT_TYPE_CHOICES = [
        ('REGULAR', 'Regular (fully-eligible or MRA+10 scenario)'),
        ('OPTIONAL', 'Optional (early out)'),
        ('DEFERRED', 'Deferred (too young, but vested to get later)'),
        ('DISABILITY', 'Disability (not already fully-eligible & must qualify)'),
    ]
    
    retirement_type = models.CharField(max_length=20, choices=RETIREMENT_TYPE_CHOICES, blank=True)
    optional_offer_date = models.DateField(null=True, blank=True, verbose_name="Optional Retirement Offer Date")
    
    # ========================================================================
    # RETIREMENT, PAY & LEAVE
    # ========================================================================
    
    # Service Computation Dates
    leave_scd = models.DateField(null=True, blank=True, verbose_name="Leave SCD")
    retirement_scd = models.DateField(null=True, blank=True, verbose_name="Retirement SCD")
    
    # Retirement Planning
    RETIREMENT_TIMING_CHOICES = [
        ('FULLY_ELIGIBLE_AGE', 'Fully-eligible (no penalty) - Age'),
        ('MRA_PLUS_10', 'MRA+10 - Date'),
    ]
    
    retirement_timing = models.CharField(max_length=25, choices=RETIREMENT_TIMING_CHOICES, blank=True)
    retirement_age = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(50), MaxValueValidator(75)])
    retirement_date = models.DateField(null=True, blank=True, verbose_name="Desired Retirement Date")
    
    # Pension Protection
    reduce_spousal_pension_protection = models.BooleanField(null=True, blank=True)
    spousal_pension_reduction_reason = models.TextField(blank=True)
    
    # Court Orders
    has_court_order_dividing_benefits = models.BooleanField(null=True, blank=True)
    court_order_details = models.TextField(blank=True)
    
    # Pay Information
    current_annual_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Current Annual Salary (with locality)")
    expects_highest_three_at_end = models.BooleanField(null=True, blank=True, verbose_name="Expects highest 3 years at end of career")
    highest_salary_history = models.TextField(blank=True, verbose_name="Highest salary history if not at end")
    
    # Leave Balances
    sick_leave_hours = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    annual_leave_hours = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    # Social Security
    ss_benefit_at_62 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Social Security Benefit at Age 62")
    ss_desired_start_age = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(62), MaxValueValidator(70)])
    ss_benefit_at_desired_age = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Notes for Page 1
    page1_notes = models.TextField(blank=True)
    
    # ========================================================================
    # PAGE 2: MILITARY SERVICE
    # ========================================================================
    
    # Military - Active Duty
    has_active_duty = models.BooleanField(null=True, blank=True)
    active_duty_start_date = models.DateField(null=True, blank=True)
    active_duty_end_date = models.DateField(null=True, blank=True)
    active_duty_deposit_made = models.BooleanField(null=True, blank=True)
    active_duty_amount_owed = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    active_duty_interrupted_service = models.BooleanField(null=True, blank=True, verbose_name="LWOP-US for active duty")
    active_duty_lwop_start = models.DateField(null=True, blank=True)
    active_duty_lwop_end = models.DateField(null=True, blank=True)
    active_duty_lwop_deposit_made = models.BooleanField(null=True, blank=True)
    active_duty_retired = models.BooleanField(null=True, blank=True)
    active_duty_pension_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    active_duty_overseas_time_added = models.BooleanField(null=True, blank=True)
    active_duty_overseas_time_amount = models.CharField(max_length=50, blank=True, verbose_name="YY/MM/DD added to SCD")
    active_duty_notes = models.TextField(blank=True)
    
    # Military - Reserves
    has_reserves = models.BooleanField(null=True, blank=True)
    reserves_start_date = models.DateField(null=True, blank=True)
    reserves_end_date = models.DateField(null=True, blank=True)
    reserves_creditable_time_years = models.PositiveIntegerField(null=True, blank=True)
    reserves_creditable_time_months = models.PositiveIntegerField(null=True, blank=True, validators=[MaxValueValidator(11)])
    reserves_creditable_time_days = models.PositiveIntegerField(null=True, blank=True, validators=[MaxValueValidator(30)])
    reserves_deposit_made = models.BooleanField(null=True, blank=True)
    reserves_amount_owed = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reserves_interrupted_service = models.BooleanField(null=True, blank=True)
    reserves_lwop_start = models.DateField(null=True, blank=True)
    reserves_lwop_end = models.DateField(null=True, blank=True)
    reserves_lwop_deposit_made = models.BooleanField(null=True, blank=True)
    reserves_retired = models.BooleanField(null=True, blank=True)
    reserves_pension_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reserves_pension_start_age = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(50), MaxValueValidator(70)])
    reserves_notes = models.TextField(blank=True)
    
    # Military - Academy
    has_academy = models.BooleanField(null=True, blank=True)
    academy_start_date = models.DateField(null=True, blank=True)
    academy_end_date = models.DateField(null=True, blank=True)
    academy_deposit_made = models.BooleanField(null=True, blank=True)
    academy_amount_owed = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    academy_appears_on_sf50 = models.BooleanField(null=True, blank=True)
    academy_notes = models.TextField(blank=True)
    
    # ========================================================================
    # PAGE 3: SPECIAL TYPES OF FEDERAL SERVICE
    # ========================================================================
    
    # Non-Deduction Service
    has_non_deduction_service = models.BooleanField(null=True, blank=True)
    non_deduction_start_date = models.DateField(null=True, blank=True)
    non_deduction_end_date = models.DateField(null=True, blank=True)
    non_deduction_deposit_made = models.BooleanField(null=True, blank=True)
    non_deduction_amount_owed = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    non_deduction_notes = models.TextField(blank=True)
    
    # Break-in-Service
    has_break_in_service = models.BooleanField(null=True, blank=True)
    break_original_start_date = models.DateField(null=True, blank=True, verbose_name="Original service start")
    break_original_end_date = models.DateField(null=True, blank=True, verbose_name="Original service end")
    break_period_start_date = models.DateField(null=True, blank=True, verbose_name="Break period start")
    break_period_end_date = models.DateField(null=True, blank=True, verbose_name="Break period end")
    break_took_refund = models.BooleanField(null=True, blank=True)
    break_made_redeposit = models.BooleanField(null=True, blank=True)
    break_amount_owed = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    break_notes = models.TextField(blank=True)
    
    # Part-Time Service
    has_part_time_service = models.BooleanField(null=True, blank=True)
    part_time_start_date = models.DateField(null=True, blank=True)
    part_time_end_date = models.DateField(null=True, blank=True)
    part_time_hours_per_week = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    part_time_contributed_to_retirement = models.BooleanField(null=True, blank=True)
    part_time_notes = models.TextField(blank=True)
    
    # Other Service Details
    other_service_history_notes = models.TextField(blank=True)
    no_special_service = models.BooleanField(default=False, verbose_name="No to ALL special service")
    
    # ========================================================================
    # PAGE 4: INSURANCE & BENEFITS
    # ========================================================================
    
    # FEGLI (Federal Employees Group Life Insurance)
    fegli_premium_line1 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="FEGLI Premium Line 1")
    fegli_premium_line2 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="FEGLI Premium Line 2")
    fegli_premium_line3 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="FEGLI Premium Line 3")
    fegli_premium_line4 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="FEGLI Premium Line 4")
    fegli_five_year_requirement_met = models.BooleanField(null=True, blank=True)
    fegli_keep_in_retirement = models.BooleanField(null=True, blank=True)
    fegli_sole_source = models.BooleanField(null=True, blank=True)
    fegli_purpose = models.CharField(max_length=200, blank=True)
    fegli_dependent_children_ages = models.CharField(max_length=200, blank=True, verbose_name="Ages of dependent children")
    fegli_notes = models.TextField(blank=True)
    
    # FEHB (Federal Employees Health Benefits)
    fehb_health_premium = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    fehb_dental_premium = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    fehb_vision_premium = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    fehb_dental_vision_premium = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="Combined Dental/Vision")
    
    FEHB_COVERAGE_CHOICES = [
        ('SELF_ONLY', 'Self-Only'),
        ('SELF_PLUS_ONE', 'Self+One'),
        ('SELF_PLUS_FAMILY', 'Self+Family'),
        ('NONE', 'None'),
    ]
    
    fehb_coverage_type = models.CharField(max_length=20, choices=FEHB_COVERAGE_CHOICES, blank=True)
    fehb_five_year_requirement_met = models.BooleanField(null=True, blank=True)
    fehb_keep_in_retirement = models.BooleanField(null=True, blank=True)
    fehb_spouse_reliant = models.BooleanField(null=True, blank=True, verbose_name="Spouse reliant on federal health benefits")
    fehb_has_tricare = models.BooleanField(null=True, blank=True)
    fehb_has_va = models.BooleanField(null=True, blank=True)
    fehb_has_spouse_plan = models.BooleanField(null=True, blank=True)
    fehb_has_private_plan = models.BooleanField(null=True, blank=True)
    fehb_notes = models.TextField(blank=True)
    
    # FLTCIP (Federal Long Term Care Insurance Program)
    fltcip_employee_premium = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    fltcip_spouse_premium = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    fltcip_other_premium = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    fltcip_daily_benefit = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(100), MaxValueValidator(450)])
    
    FLTCIP_BENEFIT_PERIOD_CHOICES = [
        ('2_YEARS', '2 years'),
        ('3_YEARS', '3 years'),
        ('5_YEARS', '5 years'),
    ]
    
    fltcip_benefit_period = models.CharField(max_length=10, choices=FLTCIP_BENEFIT_PERIOD_CHOICES, blank=True)
    
    FLTCIP_INFLATION_CHOICES = [
        ('ACIO_3PCT', 'ACIO 3%'),
        ('FPO', 'FPO'),
    ]
    
    fltcip_inflation_protection = models.CharField(max_length=10, choices=FLTCIP_INFLATION_CHOICES, blank=True)
    fltcip_want_to_discuss = models.BooleanField(null=True, blank=True, verbose_name="Want to discuss LTC options")
    fltcip_notes = models.TextField(blank=True)
    
    # ========================================================================
    # PAGE 5: TSP (Thrift Savings Plan)
    # ========================================================================
    
    # TSP Goals & Planning
    tsp_use_for_income = models.BooleanField(default=False)
    tsp_use_for_fun_money = models.BooleanField(default=False)
    tsp_use_for_legacy = models.BooleanField(default=False)
    tsp_use_for_other = models.BooleanField(default=False)
    tsp_retirement_goal_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tsp_amount_needed = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tsp_need_asap = models.BooleanField(default=False)
    tsp_need_at_age = models.PositiveIntegerField(null=True, blank=True)
    tsp_sole_source_investing = models.BooleanField(null=True, blank=True)
    tsp_sole_source_explanation = models.CharField(max_length=300, blank=True)
    
    TSP_RETIREMENT_PLAN_CHOICES = [
        ('LEAVE_IN_TSP', 'Leave in TSP'),
        ('ROLLOVER_IRA', 'Rollover to IRA'),
        ('UNSURE', 'Unsure'),
    ]
    
    tsp_retirement_plan = models.CharField(max_length=20, choices=TSP_RETIREMENT_PLAN_CHOICES, blank=True)
    
    # In-Service Withdrawal
    tsp_took_in_service_withdrawal = models.BooleanField(null=True, blank=True)
    tsp_withdrawal_financial_hardship = models.BooleanField(default=False)
    tsp_withdrawal_age_based = models.BooleanField(default=False)
    
    # New Contributions
    tsp_traditional_contribution = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Traditional contribution per pay period")
    tsp_roth_contribution = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Roth contribution per pay period")
    
    # Outstanding Loans
    tsp_general_loan_date = models.DateField(null=True, blank=True)
    tsp_general_loan_balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tsp_general_loan_repayment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Per pay period")
    tsp_general_loan_payoff_date = models.DateField(null=True, blank=True)
    
    tsp_residential_loan_date = models.DateField(null=True, blank=True)
    tsp_residential_loan_balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tsp_residential_loan_repayment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Per pay period")
    tsp_residential_loan_payoff_date = models.DateField(null=True, blank=True)
    
    # Fund Balances (existing money)
    tsp_g_fund_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tsp_f_fund_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tsp_c_fund_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tsp_s_fund_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tsp_i_fund_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tsp_l_income_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tsp_l_2025_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tsp_l_2030_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tsp_l_2035_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tsp_l_2040_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tsp_l_2045_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tsp_l_2050_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tsp_l_2055_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tsp_l_2060_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tsp_l_2065_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Fund Allocation (new money) - stored as percentages
    tsp_g_fund_allocation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    tsp_f_fund_allocation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    tsp_c_fund_allocation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    tsp_s_fund_allocation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    tsp_i_fund_allocation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    tsp_l_income_allocation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    tsp_l_2025_allocation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    tsp_l_2030_allocation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    tsp_l_2035_allocation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    tsp_l_2040_allocation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    tsp_l_2045_allocation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    tsp_l_2050_allocation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    tsp_l_2055_allocation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    tsp_l_2060_allocation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    tsp_l_2065_allocation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # Risk Tolerance & Outcomes
    tsp_employee_risk_tolerance = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(10)])
    tsp_spouse_risk_tolerance = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(10)])
    tsp_best_outcome = models.TextField(blank=True, verbose_name="Best possible outcome in retirement")
    tsp_worst_outcome = models.TextField(blank=True, verbose_name="Worst possible outcome in retirement")
    
    # TSP Comments
    tsp_comments = models.TextField(blank=True)
    
    # ========================================================================
    # PAGE 6: ADDITIONAL NOTES
    # ========================================================================
    
    additional_notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Federal Fact Finder"
        verbose_name_plural = "Federal Fact Finders"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"FFF for Case {self.case.external_case_id} - {self.employee_name}"
    
    @property
    def total_tsp_balance(self):
        """Calculate total TSP balance across all funds"""
        balances = [
            self.tsp_g_fund_balance or 0,
            self.tsp_f_fund_balance or 0,
            self.tsp_c_fund_balance or 0,
            self.tsp_s_fund_balance or 0,
            self.tsp_i_fund_balance or 0,
            self.tsp_l_income_balance or 0,
            self.tsp_l_2025_balance or 0,
            self.tsp_l_2030_balance or 0,
            self.tsp_l_2035_balance or 0,
            self.tsp_l_2040_balance or 0,
            self.tsp_l_2045_balance or 0,
            self.tsp_l_2050_balance or 0,
            self.tsp_l_2055_balance or 0,
            self.tsp_l_2060_balance or 0,
            self.tsp_l_2065_balance or 0,
        ]
        return sum(balances)
    
    @property
    def total_fegli_premium(self):
        """Calculate total FEGLI premium"""
        premiums = [
            self.fegli_premium_line1 or 0,
            self.fegli_premium_line2 or 0,
            self.fegli_premium_line3 or 0,
            self.fegli_premium_line4 or 0,
        ]
        return sum(premiums)
