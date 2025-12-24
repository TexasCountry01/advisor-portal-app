"""
Services package for cases app.
"""
# Import API integration (no WeasyPrint dependencies)
from .api_integration import benefits_api, submit_case_to_benefits_software

# PDF generator imported dynamically when needed (requires WeasyPrint system libs)
# from .pdf_generator import generate_fact_finder_pdf

__all__ = ['benefits_api', 'submit_case_to_benefits_software']
