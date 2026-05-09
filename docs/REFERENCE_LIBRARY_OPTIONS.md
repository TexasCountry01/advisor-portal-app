# Reference Document Library — Options
**Date:** May 8, 2026  
**Context:** Benefits technicians reference a ~280-page document daily to find verbiage to copy/paste into member messaging. Document is updated annually. Need: admin upload/management + technician search-and-insert tooling within the case workflow.

---

## Option A — Clause/Snippet Library (Recommended Starting Point)
**What it is:** Break the document into named, searchable text blocks ("clauses") stored in the database. Admin manages them via a CRUD interface. Technicians search while working a case and click **Insert** to drop the text directly into the case message compose box.

**How it works:**
- New `ReferenceClause` model: `title`, `category`, `body` (text), `is_active`
- Admin page: add, edit, delete, or bulk-replace clauses (can paste from Word or upload a structured file)
- On the case detail page: a **"Insert from Library"** button opens a searchable sidebar panel — technician types a keyword, matching clauses appear, one click appends the text to their message draft
- No PDF parsing required; content lives in the database and is instantly searchable

**Pros:**
- Fast search (database query)
- Zero friction to insert — technician never leaves the case page
- Survives annual updates easily — admin edits/replaces individual clauses without affecting anything else
- Works exactly where technicians already are (the case message compose box)
- No new Python dependencies required

**Cons:**
- One-time data entry effort to load the current document into clauses — estimated 2–4 hours to structure it the first time

---

## Option B — Document Upload + In-App Full-Text Search
**What it is:** Admin uploads the document (Word `.docx` or PDF) via an admin page. The system parses it, extracts the text, and stores it for full-text search. Technicians search and get paragraph-level results with an Insert button.

**How it works:**
- New `ReferenceDocument` model: stores the file + extracted plain text chunks
- On upload, parse with `python-docx` (Word) or `PyMuPDF` (PDF) to extract text into searchable segments
- Admin replaces the document annually by uploading a new file — one action, everything updates
- Same Insert-into-message UX as Option A

**Pros:**
- Admin just uploads the file — no manual data entry at all
- Annual update is a single file upload

**Cons:**
- Requires adding `python-docx` or `PyMuPDF` to `requirements.txt`
- Quality of search depends on how cleanly the source document is structured
- PDFs with complex formatting produce messy extracted text; Word `.docx` works much better
- Less control over individual clause presentation

---

## Option C — PDF Viewer with Copy (Minimal Build)
**What it is:** Admin uploads the PDF, technicians open it in a browser-based viewer and manually copy text.

**How it works:**
- File upload to the server, displayed via browser's native PDF viewer or a JS library (PDF.js)
- No parsing, no search, no insert — technician finds and copies manually as today

**Pros:**
- Minimal development work (a few hours)

**Cons:**
- Does not meaningfully solve the problem — finding verbiage in a 280-page PDF while composing a message is still cumbersome
- No improvement to the copy-paste workflow

---

## Option D — Option A + Category Tags (Full Knowledge Base)
Same as Option A but clauses are organized by **category/topic** (e.g., "Eligibility", "Survivor Benefits", "FERS vs CSRS") with a category filter alongside keyword search. Technicians can browse by topic when they don't know exactly what to search for.

- ~20% more build work than Option A
- Significantly better discoverability for technicians less familiar with the document

---

## Recommendation
**Option A to start, with Option D as a natural upgrade path.**

Option A can be built entirely within the existing Django stack with no new dependencies. The Insert button on the case detail page is the highest-value feature — it eliminates the context-switch of finding text in a separate document and manually retyping or copy-pasting it.

Option B is appealing for the annual update workflow but text extraction quality from a 280-page document is unpredictable, especially if the source is a PDF.

---

## Key Question Before Building
**Is the document structured in named sections/clauses** (e.g., "Section 4.2 — Survivor Benefit Plan Election") or is it more narrative/prose?

- **Named sections** → Option A/D is fast to import and the clause titles make search results immediately useful
- **Dense prose narrative** → Option B's paragraph-chunking approach may produce better search results, or Option A with admin-written summary titles per chunk

---

## Technical Notes (for implementation)
- Insert target: `CaseMessage` compose box on `case_detail.html`
- Admin roles: `administrator` only for manage/upload; `technician`, `manager`, `administrator` for search/insert
- Suggested new app: `knowledge/` or add to `core/`
- Model suggestion:
  ```python
  class ReferenceClause(models.Model):
      title = models.CharField(max_length=255)
      category = models.CharField(max_length=100, blank=True)
      body = models.TextField()
      is_active = models.BooleanField(default=True)
      sort_order = models.PositiveIntegerField(default=0)
      created_at = models.DateTimeField(auto_now_add=True)
      updated_at = models.DateTimeField(auto_now=True)
      created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
  ```
- Search endpoint: `/knowledge/search/?q=keyword` returning JSON for the sidebar panel
- Insert UX: JS appends clause body to the message textarea (or TinyMCE editor if applicable)
