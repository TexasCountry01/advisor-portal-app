from PyPDF2 import PdfReader

pdf_path = 'reference_PDF.pdf'
with open(pdf_path, 'rb') as f:
    reader = PdfReader(f)
    print(f'Reference PDF: {len(reader.pages)} pages\n')
    
    for page_num in range(len(reader.pages)):
        text = reader.pages[page_num].extract_text()
        lines = text.split('\n')
        # Find section headers (all caps lines)
        sections = [line.strip() for line in lines if line.strip() and all(c.isupper() or c.isspace() or c in '(),-' for c in line.strip()) and len(line.strip()) > 5]
        print(f'\n=== Page {page_num + 1} ===')
        print('Sections found:')
        for i, section in enumerate(sections[:15]):  # First 15 sections per page
            print(f'  {i+1}. {section}')
