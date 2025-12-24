#!/usr/bin/env python
"""Compare generated PDF with reference PDF to identify formatting differences."""

import pypdf

def analyze_pdf(filepath):
    """Extract detailed structure from PDF."""
    print(f"\n{'='*80}")
    print(f"Analyzing: {filepath}")
    print(f"{'='*80}")
    
    reader = pypdf.PdfReader(filepath)
    
    print(f"Number of pages: {len(reader.pages)}")
    print(f"\nPage sizes:")
    
    for i, page in enumerate(reader.pages, 1):
        box = page.mediabox
        width = float(box.width)
        height = float(box.height)
        print(f"  Page {i}: {width:.2f} x {height:.2f} pts ({width/72:.2f}\" x {height/72:.2f}\")")
    
    # Extract text from first 2 pages for structure comparison
    print(f"\n{'='*80}")
    print("TEXT CONTENT (First 2 pages):")
    print(f"{'='*80}")
    
    for i in range(min(2, len(reader.pages))):
        print(f"\n--- PAGE {i+1} ---")
        text = reader.pages[i].extract_text()
        print(text[:2000])  # First 2000 chars
        if len(text) > 2000:
            print(f"\n... ({len(text) - 2000} more characters)")

if __name__ == "__main__":
    print("\n" + "="*80)
    print("PDF COMPARISON ANALYSIS")
    print("="*80)
    
    # Analyze generated PDF
    analyze_pdf("generated_pdf.pdf")
    
    # Analyze reference PDF
    analyze_pdf("reference_pdf.pdf")
    
    print("\n" + "="*80)
    print("KEY DIFFERENCES TO CHECK:")
    print("="*80)
    print("1. Page count match")
    print("2. Page size/orientation match")
    print("3. Text layout and positioning")
    print("4. Font sizes and styling")
    print("5. Checkbox rendering")
    print("6. Table formatting")
    print("7. Section headers and spacing")
