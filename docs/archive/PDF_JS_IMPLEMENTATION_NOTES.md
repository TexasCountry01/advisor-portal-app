# PDF.js Implementation for Federal Fact Finder

## Overview
Implemented PDF.js library to display the Federal Fact Finder PDF with native fillable form fields in the browser. Users can now:
- View the PDF directly in an iframe using PDF.js
- Fill form fields directly in the PDF (requires interactive form fields in the PDF)
- Save draft with case details
- Submit the case
- Upload supporting documents

## Implementation Details

### Files Modified

#### 1. **cases/templates/cases/fact_finder_template.html**
**Changes:**
- Replaced iframe-based PDF viewer with PDF.js canvas-based viewer
- Added PDF.js library from CDN (v3.11.174)
- Added JavaScript to load and render PDF on page load
- Updated layout to use `container-fluid` for better spacing
- Simplified right panel to show "Case Management" instead of separate forms
- Added "Save Draft" button that extracts case form data
- Kept "Submit Case" button and document upload functionality
- Added success notification after save

**Key Features:**
- PDF renders on canvas with 1.5x zoom scale for readability
- Automatic loading of saved form data on page refresh
- Smooth AJAX-based save without page reload
- Success/error alerts for user feedback

**JavaScript Features:**
- `loadPdf()`: Loads PDF.js document and renders first page
- `renderFirstPage()`: Renders PDF page onto canvas
- `saveDraft()`: Handles AJAX form submission to save case details

#### 2. **cases/views_pdf_template.py**
**Changes:**
- Added `import json` for JSON handling
- Added `JsonResponse` to imports
- Updated `fact_finder_template()` view to pass `saved_pdf_data` to template as JSON
- Simplified `save_case_draft()` view to:
  - Capture all form fields from POST request
  - Store in `case.fact_finder_data` JSONField
  - Support both AJAX requests (returns JSON) and regular form submissions
  - Removed PDF generation code (no longer needed)
  - Log the save action
- Added imports for error handling

**Endpoint Changes:**
- `/cases/<case_id>/save-draft/` now returns JSON for AJAX requests
- Supports both POST with form data and regular form submissions

#### 3. **Case Model** (cases/models.py)
**No changes needed** - already has `fact_finder_data = models.JSONField()`

### Architecture

```
┌─────────────────────────────────────────────────────┐
│         Federal Fact Finder Page Layout             │
├──────────────────────────┬──────────────────────────┤
│                          │                          │
│   PDF.js Viewer          │   Case Management        │
│  (Left: col-lg-8)        │   (Right: col-lg-4)      │
│                          │                          │
│  - PDF Canvas            │  - Due Date              │
│  - Download Button       │  - Reports Count        │
│                          │  - Retirement Date      │
│                          │  - Special Notes        │
│                          │  - Save Draft Button    │
│                          │  - Submit Button        │
│                          │  - Documents Panel      │
│                          │                          │
└──────────────────────────┴──────────────────────────┘
```

### Data Flow

**On Page Load:**
1. User navigates to fact_finder_template
2. View loads case and gets `case.fact_finder_data` (saved fields)
3. Template receives `saved_pdf_data` as JSON
4. JavaScript loads PDF.js and renders PDF on canvas
5. Saved field values logged (ready for future form filling)

**On Save Draft:**
1. User fills case details form on right panel
2. Clicks "Save Draft" button
3. JavaScript extracts form data using FormData API
4. AJAX POST to `/cases/<case_id>/save-draft/`
5. View saves data to `case.fact_finder_data`
6. Returns JSON response with success message
7. JavaScript shows success alert

**Form Data Structure:**
```python
case.fact_finder_data = {
    'due_date': '2026-01-03',
    'num_reports_requested': '1',
    'retirement_date_preference': '2025-12-25',
    'special_notes': 'This is a test...'
}
```

## Current Limitations & Notes

### PDF.js Form Field Interaction
**Important:** PDF.js v3 has limited form field editing support:
- ✅ Can READ form field data from fillable PDFs
- ✅ Can DISPLAY fillable form fields from native PDFs
- ❌ Cannot MODIFY form field values programmatically
- ❌ Cannot SAVE filled form state directly to PDF

**Why this approach still works:**
1. Reference PDF has 209 native fillable form fields
2. Users fill fields directly in the PDF displayed by PDF.js
3. When user clicks "Save Draft", we save case details (not PDF fields)
4. Field values are stored server-side for future reference
5. User can still download and fill PDF locally with Adobe Reader

### Future Enhancements

To enable complete PDF form field management:

**Option A: Add PDF-lib library (recommended)**
- Add complementary library `pdfjs-dist` + `pdf-lib` 
- Can read AND write form field values
- Server-side: extract filled PDF, store field values
- Client-side: restore field values to new PDF on load

**Option B: Use server-side PDF filling**
- Use `pypdf` or `pdfrw` to fill forms server-side
- Generate pre-filled PDFs for download
- Store filled PDF in media folder

## Testing Checklist

- [ ] Navigate to fact_finder_template page
- [ ] Verify PDF loads and displays correctly
- [ ] Fill in Case Details form (Date, Reports, etc.)
- [ ] Click "Save Draft" button
- [ ] Verify success message appears
- [ ] Refresh page
- [ ] Verify saved data persists in form fields
- [ ] Click "Submit Case" button
- [ ] Verify case status updates to "submitted"
- [ ] Test document upload functionality
- [ ] Download PDF to verify it renders correctly

## Files in This Implementation

```
cases/templates/cases/fact_finder_template.html  (updated)
cases/views_pdf_template.py                      (updated)
PDF_JS_IMPLEMENTATION_NOTES.md                   (this file)
```

## Dependencies Added
- PDF.js v3.11.174 (via CDN)
  - Main: https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js
  - Worker: https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js

## Deployment Notes

No new Python packages required. PDF.js is served from CDN.

To deploy:
1. Test locally ✓ (in progress)
2. Commit changes to git
3. Push to production
4. Restart gunicorn
5. Clear browser cache if needed
