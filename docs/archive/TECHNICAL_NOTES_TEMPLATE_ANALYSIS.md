# Technical Notes Pre-Populated Template Analysis

## Date: February 15, 2026

## Stakeholder Request

Pre-populate the Technical Notes section with topic/section headers so technicians have a structured template when adding notes. Currently the notes field starts completely empty.

### Requested Template Content

```
2026 FIGURES
You will notice that the date on the front cover of the report is December 2025. We have shown this because we are working with a December pay stub. This report reflects all new 2026 figures (pay raises, COLAs, TSP contribution limits, etc.). Our software uses a 10-year average for pay raises (currently 2.11%) and the 2026 pay raise is set at 1% for most employees. See the ProFeds Annual Update for a summary of these changes. Once the employee has received the pay stub which reflects the first full pay period in January, we can revise the report.

2026 FACT FINDER
The new 2026 ProFeds Federal Fact Finder is now available! To download CLICK HERE.
  
GENERAL
 
RETIREMENT DATE
 
PAY
 
MILITARY SERVICE - ACTIVE DUTY
 
MILITARY SERVICE - RESERVES

SOCIAL SECURITY
 
FEGLI
 
FEHB
 
TSP BALANCE
 
TSP CONTRIBUTION
 
TSP FUTURE CONTRIBUTION ALLOCATION
 
BENEFICIARIES
It is always wise to ensure that employees have their beneficiaries up-to-date. To access all of the forms they'll need (a total of 4), please CLICK HERE.
```

---

## Current Implementation

### Model
- **Field:** `Case.report_notes_to_member` in `cases/models.py` (line ~303)
- **Type:** `tinymce.models.HTMLField` (rich text, stores HTML as TextField)
- **Default:** `blank=True`, no default value — starts completely empty

### Views
1. **Save Notes:** `save_report_notes()` in `cases/views.py` (~line 3390) — POST/AJAX auto-save
2. **Generate PDF:** `generate_report_notes_pdf()` in `cases/views.py` (~line 3930) — WeasyPrint HTML→PDF
3. **Upload Image:** `upload_image_for_notes()` in `cases/views.py` (~line 3824) — TinyMCE image uploads

### URL Patterns (cases/urls.py)
```python
path('<int:pk>/save-report-notes/', views.save_report_notes, name='save_report_notes')
path('<int:pk>/download-notes-pdf/', views.generate_report_notes_pdf, name='generate_report_notes_pdf')
path('upload-image/', views.upload_image_for_notes, name='upload_image_for_notes')
```

### Template (case_detail.html)
- **Read-only display:** Lines 920–966 — Members see notes when case is released; techs see read-only preview
- **Editable floating window:** Lines 3104–3135 — TinyMCE textarea for techs/admins/managers
- **TinyMCE JS init:** Lines 3253–3475 — Editor config, auto-save (1s debounce), window controls

### Data Flow
```
Tech opens case → Floating TinyMCE window (hidden by default)
  → User clicks "Notes" button → openFloatingNotes()
  → Textarea loads {{ case.report_notes_to_member|safe }} (empty initially)
  → User types → TinyMCE 'change keyup' event → 1s debounce → saveReportNotes()
  → POST /cases/<id>/save-report-notes/ → case.report_notes_to_member = notes_text → case.save()
  → Read-only cards show notes if non-empty
  → "Download as PDF" → GET /cases/<id>/download-notes-pdf/ → WeasyPrint → file download
```

---

## Implementation Options

### Option A: Populate on Case Acceptance (Recommended)
When a technician **accepts** a case, if the notes field is empty, auto-fill with template headers.

**Pros:**
- Headers appear immediately when tech opens notes
- Already-in-progress cases unaffected (field won't be empty)
- Template stored in database immediately — no risk of loss
- "CLICK HERE" links can be real HTML hyperlinks

**Cons:**
- Only applies to newly accepted cases going forward
- Template is "baked in" to Python code (needs code change to update annually)

**Implementation:** Modify the `accept_case` view to set `case.report_notes_to_member` when empty.

### Option B: Populate via TinyMCE on Editor Open
Inject template via JavaScript when TinyMCE initializes and detects empty content.

**Pros:**
- No backend changes needed
- Could work retroactively on older cases

**Cons:**
- Doesn't persist until auto-save fires (1s after any change)
- Fragile — timing issues could re-inject template
- Less reliable than backend approach

**Implementation:** Modify TinyMCE `editor.on('init')` callback in case_detail.html.

### Option C: "Insert Template" Button
Add a toolbar button that lets the tech click to insert the template at any time.

**Pros:**
- Most flexible — tech chooses when to use it
- Works on older cases too
- No accidental template injection

**Cons:**
- Risk of overwriting existing notes (needs confirmation prompt)
- Extra click required

**Implementation:** Add custom TinyMCE toolbar button in case_detail.html JS.

### Recommended Approach: Option A + Option C Combined
- Auto-populate on acceptance for new cases
- "Insert Template" button for techs who want to apply to existing cases
- Best of both worlds

---

## Open Questions

1. **"CLICK HERE" links:** Should these link to the existing Fact Finder PDF download on the portal, or an external URL?
2. **"2026 FIGURES" paragraph:** Hardcoded or configurable? (Figures change annually)
3. **Existing cases:** Apply template retroactively via button (Option C), or only new cases?

---

## Badge/Button UX Issue (Related — Separate Task)

The "Download Notes as PDF" button was flagged as part of the broader badge-vs-button color confusion issue. This is tracked separately in the colored tiles vs buttons investigation.
