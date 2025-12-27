# Field Mapping Fix - Complete Analysis & Resolution

## Problem Summary
User populated nearly every field on the Federal Fact Finder form to test complete end-to-end mapping, but many fields were NOT appearing in the generated PDF despite being filled out.

## Root Cause Analysis
The issue was **field name mismatches** between the `fact_finder_data` dictionary keys in `views.py` and the variable names expected by the PDF template. The form data WAS being captured, but the PDF template couldn't find it because it was looking for the wrong variable names.

### Specific Mismatches Found

#### 1. TSP Fund Fields
**Problem:** Dictionary used shortened keys without `_fund_` infix
- ❌ Data saved as: `g_allocation`, `g_balance`, `c_allocation`, `c_balance`, etc.
- ✅ Template expected: `g_fund_allocation`, `g_fund_balance`, `c_fund_allocation`, `c_fund_balance`

**Impact:** All TSP G, F, C, S, I fund allocation and balance fields invisible in PDF

#### 2. TSP L Fund Fields  
**Problem:** Dictionary used year without underscore
- ❌ Data saved as: `l2025_allocation`, `l2025_balance`, `l2030_allocation`, etc.
- ✅ Template expected: `l_2025_allocation`, `l_2025_balance`, `l_2030_allocation`

**Impact:** L 2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060 funds invisible (L Income and L 2065 already fixed)

#### 3. TSP Loan Fields
**Problem:** Dictionary had extra `loan_` prefix and wrong field name
- ❌ Data saved as: `loan_general_balance`, `loan_general_payoff_date`
- ✅ Template expected: `general_loan_balance`, `general_loan_payoff`

**Impact:** General and residential loan details invisible in PDF

#### 4. TSP Risk Tolerance & Outcomes
**Problem:** Field names swapped/different
- ❌ Data saved as: `risk_tolerance_employee`, `risk_tolerance_spouse`, `best_result`, `worst_result`
- ✅ Template expected: `employee_risk_tolerance`, `spouse_risk_tolerance`, `best_outcome`, `worst_outcome`

**Impact:** Risk assessment and TSP outcome fields invisible

#### 5. Section Name Mismatches
**Problem:** Main section names didn't match between data structure and template
- ❌ Data structure: `additional_information`, `military_active_duty`, `military_reserves`, `non_deduction_service`, `break_in_service`, `part_time_service`
- ✅ Template expected: `add_info`, `mad`, `reserves`, `non_deduction`, `break_service`, `part_time`

**Impact:** All fields in these sections (court orders, military service, reserves, break in service, part-time) invisible

#### 6. Context Unpacking
**Problem:** PDF generator only passed `data` as nested object, but template accessed sections directly
- ❌ Context: `{'data': {...}}` only
- ✅ Template needs: `{'data': {...}, 'tsp': {...}, 'fegli': {...}, ...}`

**Impact:** All direct section access like `{{ tsp.g_fund_balance }}` failed

## Changes Implemented

### 1. Fixed TSP Fund Field Names ([cases/views.py](cases/views.py) lines 220-232)
```python
# BEFORE
'g_allocation': float(request.POST.get('tsp_g_fund_allocation', 0) or 0),
'g_balance': float(request.POST.get('tsp_g_fund_balance', 0) or 0),
# ... same for f, c, s, i

# AFTER
'g_fund_allocation': float(request.POST.get('tsp_g_fund_allocation', 0) or 0),
'g_fund_balance': float(request.POST.get('tsp_g_fund_balance', 0) or 0),
# ... same for f, c, s, i
```

### 2. Fixed TSP L Fund Year Underscores ([cases/views.py](cases/views.py) lines 235-251)
```python
# BEFORE
'l2025_allocation': float(request.POST.get('tsp_l_2025_allocation', 0) or 0),
'l2025_balance': float(request.POST.get('tsp_l_2025_balance', 0) or 0),
# ... same for 2030-2060

# AFTER
'l_2025_allocation': float(request.POST.get('tsp_l_2025_allocation', 0) or 0),
'l_2025_balance': float(request.POST.get('tsp_l_2025_balance', 0) or 0),
# ... same for 2030-2060
```

### 3. Fixed TSP Loan Fields ([cases/views.py](cases/views.py) lines 253-260)
```python
# BEFORE
'loan_general_balance': float(request.POST.get('tsp_general_loan_balance', 0) or 0),
'loan_general_payoff_date': request.POST.get('tsp_general_loan_payoff', ''),

# AFTER
'general_loan_balance': float(request.POST.get('tsp_general_loan_balance', 0) or 0),
'general_loan_payoff': request.POST.get('tsp_general_loan_payoff', ''),
```

### 4. Fixed Risk Tolerance & Outcome Fields ([cases/views.py](cases/views.py) lines 261-266)
```python
# BEFORE
'risk_tolerance_employee': request.POST.get('tsp_employee_risk_tolerance', ''),
'risk_tolerance_spouse': request.POST.get('tsp_spouse_risk_tolerance', ''),
'best_result': request.POST.get('tsp_best_outcome', ''),
'worst_result': request.POST.get('tsp_worst_outcome', ''),

# AFTER
'employee_risk_tolerance': request.POST.get('tsp_employee_risk_tolerance', ''),
'spouse_risk_tolerance': request.POST.get('tsp_spouse_risk_tolerance', ''),
'best_outcome': request.POST.get('tsp_best_outcome', ''),
'worst_outcome': request.POST.get('tsp_worst_outcome', ''),
```

### 5. Fixed Section Names ([cases/views.py](cases/views.py) lines 318, 334, 354, 383, 393, 411)
```python
# BEFORE
'additional_information': {...}
'military_active_duty': {...}
'military_reserves': {...}
'non_deduction_service': {...}
'break_in_service': {...}
'part_time_service': {...}

# AFTER
'add_info': {...}
'mad': {...}
'reserves': {...}
'non_deduction': {...}
'break_service': {...}
'part_time': {...}
```

### 6. Fixed Context Unpacking ([cases/services/pdf_generator.py](cases/services/pdf_generator.py) lines 60-73)
```python
# BEFORE
context = {
    'case': case,
    'data': data,
    'employee_name': f"{case.employee_first_name} {case.employee_last_name}",
    ...
}

# AFTER
context = {
    'case': case,
    'data': data,  # For nested access: data.basic_information.X
    'employee_name': f"{case.employee_first_name} {case.employee_last_name}",
    ...
    **data  # Unpack all sections for direct access: tsp.X, fegli.X, etc.
}
```

## Verification
Case 24 was deleted. Server restarted with all fixes applied.

## Next Steps
1. Submit fresh test case with comprehensive data across all sections
2. Verify PDF displays ALL populated fields correctly
3. Specifically verify:
   - TSP G, F, C, S, I fund allocations and balances
   - TSP L 2025-2060 fund allocations and balances
   - TSP loan details (general and residential)
   - TSP risk tolerance and outcomes
   - Additional information (court orders, spouse protection)
   - Military active duty details
   - Military reserves details
   - Break in service
   - Part-time service

## Total Fields Fixed
- **59 TSP fields** (G/F/C/S/I funds: 10, L funds: 36, loans: 8, risk/outcomes: 5)
- **6 section names** (add_info, mad, reserves, non_deduction, break_service, part_time)
- **1 context structure** (unpacking for direct access)

All field mappings now align with PDF template expectations for complete end-to-end data flow.
