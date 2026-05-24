# Reference Library — Build Summary

**Date Built:** May 9, 2026  
**Git branch:** main  
**Status:** Built locally, pending TEST deployment

---

## Overview

A searchable reference library giving benefits technicians instant access to pre-written verbiage from the **2026 Report Notes Template** while working a case. A `📓` button in the floating Notes window header opens a slide-in panel where technicians can search, preview, and insert clauses directly into TinyMCE with one click.

---

## Source Document

- **File:** `docs/reference/2026 Report Notes Template.docx`  
  _(gitignored — do not commit; re-importable from Google Docs annually)_
- **Origin:** Google Doc → downloaded as Word (.docx)
- **Scope:** 281-page template, 6,018 paragraphs, 1,022 extractable clauses across 147 categories
- **Update cadence:** Typically once per year by an administrator

---

## Files Added

| File | Purpose |
|---|---|
| `references/__init__.py` | App package |
| `references/apps.py` | AppConfig (`verbose_name = 'Reference Library'`) |
| `references/models.py` | `ReferenceClause` model |
| `references/admin.py` | Django admin — list, search, filter, inline edit |
| `references/views.py` | Search API + reimport upload view |
| `references/urls.py` | URL routes |
| `references/migrations/0001_initial.py` | DB migration |
| `references/management/commands/import_reference_doc.py` | CLI import command |
| `references/templates/references/reimport.html` | Admin upload page |

## Files Modified

| File | Change |
|---|---|
| `config/settings.py` | Added `'references'` to `INSTALLED_APPS` |
| `config/urls.py` | Added `path('references/', include('references.urls', namespace='references'))` |
| `cases/templates/cases/case_detail.html` | Added Reference Library offcanvas panel + JS + `📓` header button |
| `requirements.txt` | Added `python-docx==1.1.2` |
| `.gitignore` | Added `docs/reference/*.docx` |

---

## Data Model

```python
class ReferenceClause(models.Model):
    category     = CharField(max_length=255)   # e.g. "VERA EARLY OUT", "TSP", "FEGLI"
    subcategory  = CharField(max_length=255)   # e.g. "ELIGIBILITY", "FACT SHEET"
    title        = CharField(max_length=500)   # e.g. "SRS Note", "Pension Begins"
    body         = TextField()                 # the verbiage to insert
    sort_order   = PositiveIntegerField()      # preserves document order
    is_active    = BooleanField(default=True)  # toggle without deleting
    created_at   = DateTimeField(auto_now_add=True)
    updated_at   = DateTimeField(auto_now=True)
```

**Heading hierarchy mapping (docx → model):**

| Word Style | Maps To |
|---|---|
| `Title` (≤120 chars) | `category` |
| `Heading 1` | `category` |
| `Heading 2` / `Heading 3` | `subcategory` |
| `Heading 4` / `Heading 5` | `title` (starts a new clause) |
| `Normal` (after a Heading 4) | `body` (accumulated lines) |

---

## API Endpoints

| Method | URL | Access | Purpose |
|---|---|---|---|
| `GET` | `/references/api/search/?q=<term>` | Login required | Returns up to 50 matching active clauses as JSON |
| `GET` | `/references/reimport/` | Administrator only | Upload form |
| `POST` | `/references/reimport/` | Administrator only | Upload `.docx` → wipe and re-import all clauses |

**Search JSON response:**
```json
{
  "results": [
    {
      "id": 42,
      "category": "VERA EARLY OUT",
      "subcategory": "ELIGIBILITY",
      "title": "SRS Note",
      "body": "While this employee is eligible for the Supplement..."
    }
  ]
}
```

---

## How Technicians Use It

1. Open a case → click **Open Notes** to show the floating notes window
2. Click the `📓` (journals) icon in the notes window header
3. The Reference Library panel slides in from the right edge
4. Type a keyword (e.g. `VERA`, `TSP`, `FEGLI`, `FEHB`, `buyback`)
5. Results appear grouped by category — click any clause to preview the full body text
6. Click **Insert into Notes** — the clause text is appended at the cursor in TinyMCE
7. Panel stays open while editing; close with the `×` button

---

## Yearly Update Workflow (Admin)

1. Open Google Doc → **File → Download → Microsoft Word (.docx)**
2. Save the file locally
3. Log in to the portal as an administrator
4. Navigate to `/references/reimport/`
5. Upload the new `.docx` → all existing clauses are replaced
6. Verify clause count shown on the page

**CLI alternative (on server):**
```bash
python manage.py import_reference_doc path/to/2027_Report_Notes_Template.docx --replace
```

---

## Ad-Hoc Clause Editing (Without Re-importing)

Administrators can edit individual clauses directly in Django admin:

- Navigate to `/admin/references/referenceclause/`
- Search, filter by category, toggle `is_active`, edit `body` text, adjust `sort_order`
- No file upload needed for minor tweaks

---

## Deployment Checklist

When deploying to TEST or PROD for the first time:

```bash
# 1. After git pull + pip install -r requirements.txt:
python manage.py migrate references

# 2. Import the reference document (copy docx to server first):
python manage.py import_reference_doc docs/reference/2026_Report_Notes_Template.docx

# 3. Restart gunicorn
```

> **Note:** The `.docx` file is gitignored. It must be copied to the server manually (scp) before running the import command, or uploaded via the `/references/reimport/` admin page.

---

## PROD Delegate Email Recipients (as of May 9, 2026)

After test account cleanup and tsdspyj reactivation:

| Email | Role |
|---|---|
| `chris@profeds.com` | Administrator/Manager |
| `devops+admin@profeds.com` | Administrator |
| `nickie@profeds.com` | Manager |
| `tiffany@profeds.com` | Level 3 Technician |
| `tsdspyj@sbcglobal.net` | Administrator (dev) |
