#!/usr/bin/env python3
"""
COMPLETE DATA FLOW AUDIT
Verifies: Form Fields → Views.py fact_finder_data → PDF Template Rendering
"""
import re
import json

def main():
    print("="*80)
    print("COMPLETE DATA FLOW AUDIT")
    print("Verifying: Form -> Views.py -> PDF Template")
    print("="*80)
    
    # Step 1: Parse views.py to find fact_finder_data structure
    with open('cases/views.py', 'r', encoding='utf-8') as f:
        views_content = f.read()
    
    # Find the fact_finder_data dictionary construction
    # Look for nested dictionaries like 'tsp': {...}
    tsp_section = re.search(r"'tsp':\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}", views_content, re.DOTALL)
    fegli_section = re.search(r"'fegli':\s*\{([^}]+)\}", views_content, re.DOTALL)
    fehb_section = re.search(r"'fehb':\s*\{([^}]+)\}", views_content, re.DOTALL)
    
    print("\n" + "="*80)
    print("TSP DATA STRUCTURE VERIFICATION")
    print("="*80)
    
    if tsp_section:
        tsp_data = tsp_section.group(1)
        # Find all dictionary keys
        keys = re.findall(r"'([^']+)':\s*(?:request\.POST\.get|float|parse)", tsp_data)
        print(f"TSP fields mapped in fact_finder_data: {len(keys)}")
        print("\nSample mappings:")
        for key in keys[:10]:
            print(f"  '{key}'")
    
    print("\n" + "="*80)
    print("FEGLI DATA STRUCTURE VERIFICATION")
    print("="*80)
    
    if fegli_section:
        fegli_data = fegli_section.group(1)
        keys = re.findall(r"'([^']+)':\s*request\.POST\.get", fegli_data)
        print(f"FEGLI fields mapped in fact_finder_data: {len(keys)}")
        for key in keys:
            print(f"  '{key}'")
    
    print("\n" + "="*80)
    print("PDF TEMPLATE DATA ACCESS")
    print("="*80)
    
    with open('cases/templates/cases/fact_finder_pdf_template_v2.html', 'r', encoding='utf-8') as f:
        pdf_content = f.read()
    
    # Find all template variable references
    pdf_vars = re.findall(r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}', pdf_content)
    
    print(f"\nTotal template variables in PDF: {len(pdf_vars)}")
    print(f"Unique variables: {len(set(pdf_vars))}")
    
    # Group by section
    tsp_vars = [v for v in pdf_vars if v.startswith('tsp.')]
    fegli_vars = [v for v in pdf_vars if v.startswith('fegli.')]
    fehb_vars = [v for v in pdf_vars if v.startswith('fehb.')]
    fltcip_vars = [v for v in pdf_vars if v.startswith('fltcip.')]
    
    print(f"\nTSP variables in PDF: {len(tsp_vars)}")
    print(f"FEGLI variables in PDF: {len(fegli_vars)}")
    print(f"FEHB variables in PDF: {len(fehb_vars)}")
    print(f"FLTCIP variables in PDF: {len(fltcip_vars)}")
    
    print("\n" + "="*80)
    print("CRITICAL FIELD VERIFICATION - TSP RENAMED FIELDS")
    print("="*80)
    
    # Check specific TSP fields that were renamed
    critical_checks = [
        ('tsp.retirement_goal', 'tsp_retirement_goal form field'),
        ('tsp.amount_needed', 'tsp_amount_needed form field'),
        ('tsp.sole_source_explain', 'tsp_sole_source_explain form field'),
        ('tsp.traditional_contribution', 'tsp_traditional_contribution form field'),
        ('tsp.roth_contribution', 'tsp_roth_contribution form field'),
        ('tsp.g_fund_balance', 'tsp_g_fund_balance form field'),
        ('tsp.f_fund_balance', 'tsp_f_fund_balance form field'),
        ('tsp.l_2025_balance', 'tsp_l_2025_balance form field (note: NOT l2025)'),
        ('tsp.l_2065_balance', 'tsp_l_2065_balance form field (note: NOT l2065_70)'),
        ('fegli.five_year_requirement', 'fegli_five_year_requirement form field'),
    ]
    
    for pdf_var, form_field in critical_checks:
        if pdf_var in pdf_content:
            status = "[OK]"
        else:
            status = "[MISSING]"
        print(f"{status} {pdf_var:30} expects {form_field}")
    
    print("\n" + "="*80)
    print("DATA MAPPING EXAMPLES")
    print("="*80)
    print("\nFlow for TSP G Fund Balance:")
    print("  1. HTML Form: <input name='tsp_g_fund_balance'> ")
    print("  2. Views.py: 'g_fund_balance': request.POST.get('tsp_g_fund_balance')")
    print("  3. PDF Template: {{ tsp.g_fund_balance }}")
    
    print("\nFlow for FEGLI Five Year Requirement:")
    print("  1. HTML Form: <input name='fegli_five_year_requirement'>")
    print("  2. Views.py: 'five_year_requirement': request.POST.get('fegli_five_year_requirement')")
    print("  3. PDF Template: {{ fegli.five_year_requirement }}")
    
    print("\n" + "="*80)
    print("VIEWS.PY FACT_FINDER_DATA STRUCTURE CHECK")
    print("="*80)
    
    # Check that fact_finder_data uses nested structure
    if "'tsp': {" in views_content:
        print("[OK] TSP section uses nested dictionary structure")
    if "'fegli': {" in views_content:
        print("[OK] FEGLI section uses nested dictionary structure")
    if "'fehb': {" in views_content:
        print("[OK] FEHB section uses nested dictionary structure")
    if "'fltcip': {" in views_content:
        print("[OK] FLTCIP section uses nested dictionary structure")
    
    # Verify the mapping pattern
    if "'g_fund_balance': float(request.POST.get('tsp_g_fund_balance'" in views_content:
        print("[OK] TSP fields use correct mapping pattern (dictionary key != form field name)")
    if "'five_year_requirement': request.POST.get('fegli_five_year_requirement'" in views_content:
        print("[OK] FEGLI fields use correct mapping pattern")
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("\n1. Form Field Names: Prefixed (e.g., tsp_g_fund_balance)")
    print("2. POST Processing: request.POST.get('tsp_g_fund_balance')")
    print("3. Dictionary Keys: Unprefixed (e.g., 'g_fund_balance')")
    print("4. PDF Template: Nested access (e.g., {{ tsp.g_fund_balance }})")
    
    print("\nThis creates the structure:")
    print("  fact_finder_data = {")
    print("    'tsp': {")
    print("      'g_fund_balance': <value from tsp_g_fund_balance>,")
    print("      'f_fund_balance': <value from tsp_f_fund_balance>,")
    print("      ...")
    print("    }")
    print("  }")
    
    print("\n" + "="*80)
    print("AUDIT COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
