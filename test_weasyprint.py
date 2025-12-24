"""
Quick test script to verify WeasyPrint installation
Run: python test_weasyprint.py
"""
try:
    from weasyprint import HTML, CSS
    print("✓ WeasyPrint imported successfully!")
    
    # Try generating a simple PDF
    html_content = """
    <!DOCTYPE html>
    <html>
    <head><title>Test PDF</title></head>
    <body>
        <h1>WeasyPrint Test</h1>
        <p>If you can see this PDF, WeasyPrint is working correctly!</p>
    </body>
    </html>
    """
    
    pdf = HTML(string=html_content).write_pdf('test_output.pdf')
    print("✓ PDF generated successfully!")
    print("✓ Check test_output.pdf in the current directory")
    
except OSError as e:
    print(f"✗ GTK libraries not found: {e}")
    print("\nInstall GTK Runtime from:")
    print("https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases")
except Exception as e:
    print(f"✗ Error: {e}")
