# Notes Reference Library — Enhancement Options

**Date:** June 2026  
**Status:** Analysis only — no code changes  
**Purpose:** Document options for enhancing the Reference Library feature based on the technician wish list

---

## Current State Summary

The Reference Library was built in May 2026. Key facts:

- **1,022 clauses** across **147 categories**, parsed from the 281-page ProFeds Word template
- **Storage model:** `ReferenceClause` — fields: `category`, `subcategory`, `title`, `body` (plain TextField), `sort_order`, `is_active`
- **Search:** GET `/references/api/search/?q=<term>` — case-insensitive keyword match across all four text fields, returns up to 50 results as JSON
- **Import:** `python-docx` CLI command + admin reimport page; uses a state machine parser that extracts `.text` only — **all Word formatting is discarded**
- **UI:** Slide-in panel on `case_detail.html`, inline drill-down preview, single "Insert into Notes" button
- **Insertion:** Calls `tinymce.execCommand('mceInsertContent')` with `<p>` + `clause.body.replace(/\n/, '<br>')` — **plain text only**

---

## Wish List Items

### 1. Rich Text / Formatting Preservation
### 2. Highlighted "Update Me" Cues
### 3. Clickable Hyperlinks in PDF
### 4. Image Support
### 5. Browse by Section
### 6. Search Within a Section
### 7. "Common Notes" per Section (Pinned / Featured)
### 8. Recently Used Clauses

---

## Item 1 — Rich Text / Formatting Preservation

### Problem
The current `_parse_document()` parser calls `para.text` (a `python-docx` shortcut that concatenates all run text). This discards:
- Bold, italic, underline formatting
- Colored text and yellow highlights
- Bullet lists and numbered lists
- Hyperlinks embedded in runs

The plain text is then inserted into TinyMCE as raw `<br>` breaks, so the notes editor shows an unformatted wall of text.

### Option A — Store HTML in the `body` field (Recommended)
Change `import_reference_doc.py` to iterate `para.runs` and emit HTML tags for each run's formatting:
- `run.bold` → `<strong>`
- `run.italic` → `<em>`
- `run.underline` → `<u>`
- `run.font.color.rgb` → `<span style="color: #RRGGBB">`
- Paragraph style (List Bullet, List Number) → `<ul>/<li>` or `<ol>/<li>` grouping
- Hyperlinks: iterate `para._p.xml` for `<w:hyperlink>` elements

The `body` field stays as TextField (HTML string). No schema change needed.  
The `insertClause()` JS function already calls `mceInsertContent` — replace the plain-text builder with `editor.execCommand('mceInsertContent', false, clause.body)` directly.  

**Pros:** No model migration; HTML is already what TinyMCE expects; one-time re-import replaces all existing clauses cleanly via the existing admin reimport page.  
**Cons:** Parser complexity increases; some edge cases (tables, nested lists) may need manual cleanup after import.  
**Effort:** Medium — 3–5 hours for a robust run-to-HTML converter + re-import + spot-check.

### Option B — Store Markdown, convert on insert
Parse runs to Markdown (e.g. `**bold**`, `- bullet`) and store in `body`. Convert Markdown → HTML in the browser before inserting into TinyMCE.

**Pros:** Markdown is human-readable in admin; easier to hand-edit individual clauses.  
**Cons:** Requires a JS Markdown parser (e.g. `marked.js`); Markdown ↔ Word round-trip is lossy for colored text and hyperlinks; admin editing is harder for non-technical users.  
**Effort:** Similar to Option A but adds a browser dependency.

### Option C — Do nothing for this annual cycle
Live with plain text. Technicians can manually bold/italicize after inserting.

**Pros:** Zero effort.  
**Cons:** Defeats the purpose of the library for formatted content; highlights and hyperlinks are silently lost.

### Recommendation
**Option A.** The `body` field already accepts arbitrary text; swapping the parser to emit HTML and changing one line of JS is the cleanest path. Re-import via the admin reimport page is already supported.

---

## Item 2 — Highlighted "Update Me" Cues

### Problem
The Word template uses yellow highlights on text that technicians must personalize (e.g., `[Member's name]`, date fields, percentage figures). These highlights are stripped during import.

### Option A — Preserve highlight as `<mark>` (pairs with Item 1 Option A)
In the run-to-HTML converter, check `run.font.highlight_color` (or `run.font.color` if yellow). Emit `<mark>` for yellow-highlighted runs, or `<span style="background-color: #FFFF00">`.

TinyMCE displays `<mark>` tags natively. The technician sees exactly which values need personalizing before inserting.

**Pros:** Visual fidelity matches the source document; no new model fields; `<mark>` is semantic HTML.  
**Cons:** If the year-to-year template changes highlight colors for other purposes, the detector may need tuning.

### Option B — Custom placeholder syntax
On import, detect highlighted text and wrap it in a custom token: `{{UPDATE: Member Name}}`. Display these tokens in the panel with a yellow chip style. On insertion, convert tokens to `<span class="update-cue">` so they appear highlighted in TinyMCE.

**Pros:** More structured; enables a future "unfilled placeholder" warning.  
**Cons:** Requires a second parse pass to detect boundaries; tokens could be accidentally left in finished notes.

### Option C — Admin-curated `has_update_cues` flag
Add a boolean field to `ReferenceClause`. Admins mark clauses that require personalization. The panel shows a ⚠ badge but doesn't highlight individual words.

**Pros:** Simpler; survives re-import.  
**Cons:** Doesn't tell the technician *which* words need updating; requires manual admin curation after every annual re-import.

### Recommendation
**Option A** — implement `<mark>` detection in the HTML parser as a natural extension of Item 1 Option A.

---

## Item 3 — Clickable Hyperlinks in PDF

### Problem
The Word template contains hyperlinks (e.g., OPM.gov links, FEHB plan finder). These are stripped on import. Technicians cannot currently insert linked text into notes.

Separately: the notes-to-PDF renderer (`generate_report_notes_pdf` view) renders `report_notes_to_member` HTML via WeasyPrint. WeasyPrint supports `<a href>` tags and renders them as clickable links in PDF output.

### Option A — Preserve `<a>` tags in HTML body (pairs with Item 1 Option A)
In the run-to-HTML converter, iterate `para._p` for `<w:hyperlink r:id="...">` elements, look up the relationship target in `doc.part.rels`, and emit `<a href="URL">text</a>`.

**Pros:** Links work in both TinyMCE (live editor) and WeasyPrint (PDF output) with no extra work; no model changes.  
**Cons:** Hyperlinks in .docx use relationship IDs; the parser must walk `_p.xml` rather than the high-level API — slightly more complex.  
**Effort:** 2–3 hours, including testing that the generated PDF contains clickable links.

### Option B — Manual link insertion via TinyMCE
Leave the library as-is. Technicians manually add links in TinyMCE using the existing link toolbar button.

**Pros:** Zero parser work.  
**Cons:** Technicians must remember to add links each time; inconsistent across completed cases.

### Recommendation
**Option A.** Part of the same parser rewrite as Items 1 and 2.

---

## Item 4 — Image Support

### Problem
The Word template contains approximately 70 screen captures (e.g., OPM online system screenshots, example forms). These are embedded images and are completely ignored by the current parser.

This is the most technically complex wish list item and has the most tradeoffs.

### Option A — Extract images into Django media storage on import
`python-docx` exposes `doc.inline_shapes` and paragraph-level image relationships. On import, save each image to `media/reference_images/<hash>.png` and embed `<img src="/media/reference_images/...">` in the clause body HTML.

**Pros:** Images appear inline in TinyMCE when the clause is previewed; images appear in the PDF via WeasyPrint.  
**Cons:**  
- Most screen captures are of OPM/agency systems that change annually — images will go stale immediately at next annual re-import.  
- Images are large; duplicated across every re-import unless de-duplicated by hash.  
- A clause with a full-page screenshot does not insert cleanly into a paragraph-based notes document.  
- Storage cost: 70 images × ~200KB avg = ~14MB per import; manageable but grows.

### Option B — Link to images in an external shared folder
Don't embed images in the body field. Instead, create a separate `ReferenceImage` model and an image viewer modal in the panel. Technicians can view the image in context but must manually incorporate any relevant information into their notes.

**Pros:** Keeps the clause body lightweight; images can be updated independently of text.  
**Cons:** Separate model and import logic; panel UI needs an image browser.

### Option C — Exclude images from the library (Recommended for now)
Do not import images. Add a note in the panel UI: *"Image references in this section — see [source template link]."*  

Rationale: The ~70 images are primarily OPM system screenshots used for advisor guidance, not content that belongs in member-facing notes. Technicians who need to reference them should consult the source template or a shared drive copy.  

**Pros:** Zero complexity; eliminates staleness problem entirely.  
**Cons:** Some advisor guidance context is lost in the panel.

### Option D — Add an `image_note` TextField
During import, detect that a paragraph precedes or follows an image and store a text summary like `[Image: Example of the OPM online services login screen — see source template]` in the body.

**Pros:** Preserves context without storing binary data; simple to implement.  
**Cons:** Requires manual annotation during import or a fragile heuristic.

### Recommendation
**Option C** for the current cycle. Revisit if the template images stabilize year-over-year. If desired, combine with **Option D** to at least surface a placeholder in the body text.

---

## Item 5 — Browse by Section (Without a Search Term)

### Problem
The current panel requires a search term — there is no way to browse all clauses hierarchically by category. Technicians who want to review an entire section (e.g., "FEHB" or "TSP Withdrawal") must type a broad term and hope it surfaces the right clauses.

### Option A — Add a Browse mode tab to the panel
Add a second tab ("Browse") alongside the existing search input. On click:
1. A new API endpoint `GET /references/api/categories/` returns the category/subcategory tree.
2. The panel renders an accordion: **Category → Subcategory → Clause list**.
3. Clicking a clause opens the existing inline preview/insert flow.

**Pros:** Familiar accordion UI; complements search rather than replacing it; no model changes.  
**Cons:** 147 categories would produce a long accordion; needs lazy loading (subcategories fetched on expand) to remain responsive.  
**Effort:** Medium — 1 new API endpoint + new panel tab HTML + accordion JS.

### Option B — Category-first panel (replace search as default)
Make the panel default to a category list. Clicking a category shows its clauses. Search becomes a secondary mode accessible via a "Search" link.

**Pros:** More structured for methodical technicians who work section-by-section.  
**Cons:** Slower for technicians who know what they're looking for; changes the established UX flow.

### Option C — Add category filter chips above search results
After a search, show category filter chips (like faceted search). Clicking "TSP" filters the results to TSP-category clauses only.

**Pros:** Blends browsing and search; low UI footprint.  
**Cons:** Only useful after a search, not for pure browsing.

### Recommendation
**Option A** (Browse tab). The two-mode approach (Search + Browse) serves both usage patterns and is consistent with how the current panel is structured.

---

## Item 6 — Search Within a Section

### Problem
The current search queries all clauses globally. A technician working a TSP case may get FEHB results mixed in with TSP results for a term like "withdrawal" that appears in multiple sections.

### Option A — Category filter in the search API
Extend the existing `search_clauses` view to accept an optional `?category=<name>` query parameter. In the panel, add a category dropdown (populated from `ReferenceClause.objects.values_list('category', flat=True).distinct()`) that pre-filters results.

**Pros:** Simple API change; minimal UI addition; combines well with Option A from Item 5 (if browsing to a category, the search input auto-scopes to that category).  
**Cons:** Category names can be long; dropdown UX requires care on a narrow panel.

### Option B — Search scoped automatically when in Browse mode
When the technician is viewing a category in Browse mode (Item 5 Option A), type-to-search within that category only. Returning to the root resets to global search.

**Pros:** Natural context — scope follows where the technician is browsing.  
**Cons:** Only useful if Browse mode is implemented first.

### Recommendation
**Option B** as a natural complement to Item 5 Option A. If Browse mode is not built, fall back to **Option A** as a standalone filter.

---

## Item 7 — "Common Notes" per Section (Pinned / Featured)

### Problem
Certain clauses are used on virtually every case (e.g., CSRS vs FERS determination language, standard FEHB election explanation). There is no way to surface the top 5–10 most-used clauses for a given case type without searching.

### Option A — `is_featured` boolean flag on the model
Add a `is_featured = BooleanField(default=False)` to `ReferenceClause`. Admins check this in the Django admin for high-frequency clauses (e.g., 20–30 clauses). The panel shows a "Common Notes" section at the top of search results or Browse mode when no search term is typed.

**Pros:** Admin-curated; stable; no usage tracking overhead; survives re-import if the migration seeds featured flags from a separate fixture.  
**Cons:** Manual curation required after each annual re-import; admin must remember which clauses are featured.  
**Re-import note:** `reimport_view` currently `ReferenceClause.objects.all().delete()` before re-importing. The `is_featured` flags would be wiped. Solution: save featured clause titles before wipe, restore after, or use a separate fixture file.

### Option B — Usage count tracking
Add a `usage_count = IntegerField(default=0)` to `ReferenceClause`. Each time `insertClause()` fires, POST to a lightweight endpoint `PATCH /references/api/clauses/<id>/record-use/` that increments the counter. Show the top-N by `usage_count` per category.

**Pros:** Organic, self-maintaining; reflects actual usage patterns; no admin curation needed.  
**Cons:** Usage counts are per-installation (not per-user); same re-import wipe problem as Option A; early data is noisy until there is sufficient volume.

### Option C — Usage count + `is_featured` hybrid
Mark a starter set of featured clauses on initial import (via import script or fixture). Let usage counts accumulate over time and promote high-use clauses automatically.

**Pros:** Best of both worlds.  
**Cons:** More model fields; re-import wipe still needs to be handled.

### Recommendation
**Option A** to start. It is the simplest and most maintainable approach. Add a note in the import command to print a reminder: *"Remember to re-mark featured clauses after reimport."* Upgrade to Option B if usage tracking becomes valuable.

---

## Item 8 — Recently Used Clauses

### Problem
Technicians frequently insert the same 5–10 clauses across many cases. Currently they must search each time.

### Option A — Browser `localStorage` (No Server Changes)
After every `insertClause()` call, push `{ id, title, category }` to a JSON array in `localStorage['refLib_recent']` (capped at the last 25 entries). On panel open, if no search term is active, render a "Recently Used" section from `localStorage`.

**Pros:** Zero server changes; instant UX; works per-browser (appropriate since one tech per browser).  
**Cons:** Resets if the user clears browser data; not shared across devices; no analytics.  
**Effort:** Very low — ~20 lines of JS in `insertClause()` and the panel open handler.

### Option B — Server-side `ReferenceUsage` model
Create a new model: `ReferenceUsage(user, clause, used_at)`. On insert, POST to `POST /references/api/clauses/<id>/record-use/`. The search API returns the user's last 10 used clauses when `?mode=recent` is passed.

**Pros:** Persists across browsers and devices; enables cross-user analytics.  
**Cons:** Adds a model, migration, view, and endpoint; growing table (1 row per insert per user per case); privacy/GDPR consideration if usage is PII.

### Option C — Session-based recent list
Store the recent list in the Django session (cleared when the user logs out). A middleware or a simple session key `request.session['recent_clauses']` is updated on each insert API call.

**Pros:** No permanent storage; clears on logout (appropriate for a work session); simple implementation.  
**Cons:** Session-scoped only (reset on each login); less persistent than Option B.

### Recommendation
**Option A** (localStorage) for immediate value with no backend work. If cross-device persistence or analytics become needed, migrate to **Option B**.

---

## Implementation Priority Matrix

| # | Item | Complexity | Impact | Dependencies | Recommended Approach |
|---|------|-----------|--------|-------------|---------------------|
| 1 | Rich Text Preservation | Medium | High | None | Option A — HTML in body field |
| 2 | Highlight "Update Me" Cues | Low | High | Item 1 | Option A — `<mark>` in HTML parser |
| 3 | Clickable Hyperlinks | Low-Med | Medium | Item 1 | Option A — `<a>` tags in parser |
| 4 | Image Support | High | Low | Item 1 | Option C — Exclude for now |
| 5 | Browse by Section | Medium | High | None | Option A — Browse tab |
| 6 | Search Within Section | Low | Medium | Item 5 | Option B — scoped to Browse mode |
| 7 | Common Notes (Pinned) | Low | High | None | Option A — `is_featured` flag |
| 8 | Recently Used | Very Low | High | None | Option A — localStorage |

### Suggested Build Sequence

**Phase 1 — High value, backend parser rewrite**  
Items 1 + 2 + 3 together (one parser rewrite, one reimport). This is the single highest-impact change and affects ~1,022 existing clauses immediately.

**Phase 2 — UI enhancements (no model changes)**  
Item 8 (localStorage recent list) and Item 7 (`is_featured` flag + admin curation). These can be done independently and quickly.

**Phase 3 — Browse mode**  
Items 5 + 6 together. New API endpoint + panel tab. No model changes.

**Phase 4 — Images (if desired)**  
Re-evaluate after Phase 1–3 are complete.

---

## Technical Notes

### Re-import Wipe Issue (Items 1, 7)
The current `reimport_view` does `ReferenceClause.objects.all().delete()` before re-importing. Any added fields that are admin-curated (`is_featured`, manual body edits) will be wiped.

**Solution strategies:**
- Before wipe, export featured clause titles to a JSON fixture; restore after import by matching on `title`.
- Change the import to be additive (update-or-create by title) instead of wipe-and-reload. This preserves manually-curated fields but risks orphan clauses if the source document renames sections.

### HTML Sanitization
If the `body` field stores HTML, the existing `insertClause()` call passes it directly to TinyMCE via `mceInsertContent`. TinyMCE sanitizes its own input, so this is safe for the editor. However, the `body` field should never be rendered `|safe` in a Django template without sanitization (e.g., via `bleach`).  
Current usage: the body is only sent as JSON via the search API and consumed by TinyMCE JS — there is no direct template rendering of `body`, so no immediate risk.

### Parser Scope
The import command `references/management/commands/import_reference_doc.py` currently handles `.docx` files only. The annual template is maintained in Google Docs and exported to `.docx` before import. Any formatting introduced in Google Docs that is not exported cleanly to `.docx` (e.g., Google Docs "Suggestions" mode, comments) will still be lost.

---

*This document is an analysis only. No code changes have been made.*

---

## TODO — Implementation Checklist

### Phase 1 — Parser Rewrite (Items 1 + 2 + 3) — HIGH PRIORITY
- [ ] **1.1** Rewrite `_parse_document()` in `import_reference_doc.py` to walk `para._p` XML and emit HTML for each run (bold → `<strong>`, italic → `<em>`, underline → `<u>`, color → `<span style="color:…">`)
- [ ] **1.2** Detect yellow highlight (`<w:highlight w:val="yellow">`) and emit `<mark>` tags
- [ ] **1.3** Detect `<w:hyperlink r:id="…">` elements, resolve URL from `doc.part.rels`, emit `<a href="…" target="_blank">` wrapping the link runs
- [ ] **1.4** Detect list paragraph styles (`List Bullet*` → `<ul><li>`, `List Number*` → `<ol><li>`) and group consecutive items
- [ ] **1.5** Update `insertClause()` JS: use `clause.body` directly (it is now HTML — no escaping, no `\n` replace)
- [ ] **1.6** Update clause preview in panel: render `clause.body` as `innerHTML` (not `escHtml(...)`)
- [ ] **1.7** Re-import the Word document on LOCAL to populate HTML bodies
- [ ] **1.8** Spot-check 5–10 clauses in the panel for correct rendering

### Phase 2 — Featured Clauses + Recently Used (Items 7 + 8)
- [ ] **2.1** Add `is_featured = BooleanField(default=False)` to `ReferenceClause` model
- [ ] **2.2** Create and run Django migration
- [ ] **2.3** Update `ReferenceClauseAdmin` to show, filter, and list-edit `is_featured`
- [ ] **2.4** Update `reimport_view` to capture featured clause titles before wipe and restore the flag after re-import (match by title)
- [ ] **2.5** Update `search_clauses` API to include `is_featured` in JSON results
- [ ] **2.6** Add `GET /references/api/featured/` endpoint — returns featured clauses, optionally scoped by `?category=`
- [ ] **2.7** Update panel JS: on open (or when search cleared), show "Common Notes" section loaded from the featured endpoint, then "Recently Used" from `localStorage`
- [ ] **2.8** Update `insertClause()` JS to push `{id, title, category, subcategory, body}` to `localStorage['refLib_recent']`, capped at 25
- [ ] **2.9** Curate initial `is_featured` set in Django admin (admin responsibility after re-import)

### Phase 3 — Browse Mode (Items 5 + 6)
- [ ] **3.1** Add `GET /references/api/categories/` endpoint — returns category/subcategory tree with clause counts
- [ ] **3.2** Update `search_clauses` to accept optional `?category=<name>` parameter for scoped search
- [ ] **3.3** Add "Browse" tab alongside the existing search input in the Reference Library panel
- [ ] **3.4** Implement category accordion in Browse tab (lazy-loads subcategories on expand)
- [ ] **3.5** When a category is active in Browse mode, scope the search input to that category only
- [ ] **3.6** "Back to all categories" button to reset scope

### Phase 4 — Images (Deferred)
- [ ] **4.1** Re-evaluate after Phase 1–3 complete — consider Option D (image placeholder text) if desired

### Re-Import Workflow Reminder
After each annual re-import:
1. Run `python manage.py import_reference_doc <new_file.docx> --replace` (or use admin reimport page — it now auto-restores featured flags)
2. Spot-check HTML rendering of 10 clauses in the panel
3. Re-curate any NEW clauses as featured in Django admin (the restore only covers clauses whose title matched the previous import)
