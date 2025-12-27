#!/usr/bin/env python3
"""
Complete Field Audit - ALL FIELDS
Verifies every field on the form is properly mapped and saved
"""
import re
import json

def extract_form_fields():
    """Extract all field names from HTML form"""
    with open('cases/templates/cases/fact_finder_form.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Extract all name attributes
    form_fields = set(re.findall(r'name=["\']([^"\']+)["\']', html))
    return sorted(form_fields)

def extract_fact_finder_data_fields():
    """Extract all fields captured in fact_finder_data"""
    with open('cases/views.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all request.POST.get calls
    post_gets = re.findall(r"request\.POST\.get\(['\"]([^'\"]+)['\"]", content)
    return sorted(set(post_gets))

def extract_pdf_template_fields():
    """Extract all fields referenced in PDF template"""
    with open('cases/templates/cases/fact_finder_pdf_template_v2.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all {{ variable }} references
    variables = re.findall(r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}', content)
    return sorted(set(variables))

def main():
    print("="*80)
    print("COMPLETE FIELD AUDIT - ALL FIELDS")
    print("="*80)
    
    form_fields = extract_form_fields()
    post_fields = extract_fact_finder_data_fields()
    pdf_fields = extract_pdf_template_fields()
    
    print(f"\nHTML Form Fields: {len(form_fields)}")
    print(f"Views.py POST.get Fields: {len(post_fields)}")
    print(f"PDF Template Variables: {len(pdf_fields)}")
    
    print("\n" + "="*80)
    print("FORM FIELDS NOT IN VIEWS.PY")
    print("="*80)
    missing_in_views = set(form_fields) - set(post_fields)
    if missing_in_views:
        for i, field in enumerate(sorted(missing_in_views), 1):
            print(f"{i:3}. {field}")
    else:
        print("[OK] ALL FORM FIELDS CAPTURED IN VIEWS.PY")
    
    print("\n" + "="*80)
    print("COMPLETE FIELD LIST (Alphabetical)")
    print("="*80)
    for i, field in enumerate(form_fields, 1):
        in_views = "OK" if field in post_fields else "MISSING"
        print(f"{i:3}. {in_views:7} {field}")
    
    # Check TSP fields specifically
    print("\n" + "="*80)
    print("TSP FIELD VERIFICATION (51 renamed fields)")
    print("="*80)
    tsp_checks = [
        ('tsp_retirement_goal', 'tsp_goal_amount'),
        ('tsp_amount_needed', 'tsp_need_amount'),
        ('tsp_sole_source_explain', 'tsp_sole_explain'),
        ('tsp_traditional_contribution', 'tsp_traditional_contributions'),
        ('tsp_roth_contribution', 'tsp_roth_contributions'),
        ('tsp_general_loan_date', 'tsp_loan_general_date'),
        ('tsp_general_loan_balance', 'tsp_loan_general_balance'),
        ('tsp_general_loan_repayment', 'tsp_loan_general_repayment'),
        ('tsp_general_loan_payoff', 'tsp_loan_general_payoff_date'),
        ('tsp_residential_loan_date', 'tsp_loan_residential_date'),
        ('tsp_residential_loan_balance', 'tsp_loan_residential_balance'),
        ('tsp_residential_loan_repayment', 'tsp_loan_residential_repayment'),
        ('tsp_residential_loan_payoff', 'tsp_loan_residential_payoff_date'),
        ('tsp_g_fund_balance', 'tsp_g_balance'),
        ('tsp_f_fund_balance', 'tsp_f_balance'),
        ('tsp_c_fund_balance', 'tsp_c_balance'),
        ('tsp_s_fund_balance', 'tsp_s_balance'),
        ('tsp_i_fund_balance', 'tsp_i_balance'),
        ('tsp_g_fund_allocation', 'tsp_g_allocation'),
        ('tsp_f_fund_allocation', 'tsp_f_allocation'),
        ('tsp_c_fund_allocation', 'tsp_c_allocation'),
        ('tsp_s_fund_allocation', 'tsp_s_allocation'),
        ('tsp_i_fund_allocation', 'tsp_i_allocation'),
        ('tsp_l_2025_balance', 'tsp_l2025_balance'),
        ('tsp_l_2030_balance', 'tsp_l2030_balance'),
        ('tsp_l_2035_balance', 'tsp_l2035_balance'),
        ('tsp_l_2040_balance', 'tsp_l2040_balance'),
        ('tsp_l_2045_balance', 'tsp_l2045_balance'),
        ('tsp_l_2050_balance', 'tsp_l2050_balance'),
        ('tsp_l_2055_balance', 'tsp_l2055_balance'),
        ('tsp_l_2060_balance', 'tsp_l2060_balance'),
        ('tsp_l_2065_balance', 'tsp_l2065_70_balance'),
        ('tsp_l_2025_allocation', 'tsp_l2025_allocation'),
        ('tsp_l_2030_allocation', 'tsp_l2030_allocation'),
        ('tsp_l_2035_allocation', 'tsp_l2035_allocation'),
        ('tsp_l_2040_allocation', 'tsp_l2040_allocation'),
        ('tsp_l_2045_allocation', 'tsp_l2045_allocation'),
        ('tsp_l_2050_allocation', 'tsp_l2050_allocation'),
        ('tsp_l_2055_allocation', 'tsp_l2055_allocation'),
        ('tsp_l_2060_allocation', 'tsp_l2060_allocation'),
        ('tsp_l_2065_allocation', 'tsp_l2065_70_allocation'),
        ('tsp_employee_risk_tolerance', 'risk_tolerance_employee'),
        ('tsp_spouse_risk_tolerance', 'risk_tolerance_spouse'),
        ('tsp_risk_tolerance_why', 'risk_tolerance_why'),
        ('tsp_best_outcome', 'tsp_best_result'),
        ('tsp_worst_outcome', 'tsp_worst_result'),
        ('fegli_five_year_requirement', 'fegli_5_years_coverage'),
    ]
    
    for new_name, old_name in tsp_checks:
        new_in_form = new_name in form_fields
        old_in_form = old_name in form_fields
        new_in_views = new_name in post_fields
        old_in_views = old_name in post_fields
        
        if new_in_form and new_in_views and not old_in_form and not old_in_views:
            status = "[OK] CORRECT"
        elif old_in_form or old_in_views:
            status = "[ERROR] OLD NAME FOUND"
        else:
            status = "[WARN] CHECK"
        
        print(f"{status} {new_name}")
        if old_in_form:
            print(f"    [ERROR] OLD NAME IN FORM: {old_name}")
        if old_in_views:
            print(f"    [ERROR] OLD NAME IN VIEWS: {old_name}")

if __name__ == "__main__":
    main()
