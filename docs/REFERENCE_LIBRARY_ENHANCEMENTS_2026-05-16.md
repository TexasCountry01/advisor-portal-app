# Reference Library — Enhancement Release Notes

**Date:** May 16, 2026
**Branch:** `feature/reference-library`
**Status:** Deployed to TEST

---

## Summary

Full enhancement pass on the Reference Library panel based on the `REFERENCE_LIBRARY_ENHANCEMENT_OPTIONS.md` wish list, plus iterative UI/UX bug fixes found during testing.

---

## Changes by File

### `references/management/commands/import_reference_doc.py`
- **Parser rewrite (Phase 1):** replaced `para.text` with a run-by-run HTML emitter
  - Bold → `<strong>`, italic → `<em>`, underline → `<u>`
  - Font color → `<span style="color:#RRGGBB">`
  - Yellow highlight → `<mark>`
  - Hyperlinks (via `<w:hyperlink>` relationships) → `<a href="..." target="_blank">`
  - List Bullet / List Number paragraph styles → `<ul><li>` / `<ol><li>` with consecutive-item grouping
- Result: 1,438 clauses with full HTML bodies (up from 1,022 plain-text clauses)
- `POSTPONED` and other heading-only clauses now correctly captured as standalone clauses

### `references/models.py`
- Added `is_featured = BooleanField(default=False)` to `ReferenceClause`
- Supports "Common Notes" section in the panel (admin-curated)

### `references/migrations/0004_referenceclause_is_featured.py`
- Migration for the `is_featured` field

### `references/admin.py`
- Added `is_featured` to list display, list filter, and list-editable columns
- Allows bulk-marking of Common Notes clauses without opening each one individually

### `references/views.py`
- `search_clauses`: title/category/subcategory matches returned first; body-only matches after; 200-result cap; optional `?category=` scope param
- `featured_clauses` (`/api/featured/`): returns `is_featured=True` clauses
- `clauses_by_category` (`/api/clauses/`): returns all clauses when no `?category=` given (used by Browse All); returns category-scoped clauses when param present
- `clause_detail` (`/api/clause/<id>/`): single-clause fallback endpoint for stale localStorage entries
- `reimport_view`: captures featured clause titles before wipe, restores `is_featured` flag after reimport by title match

### `references/urls.py`
- Added `/api/clause/<id>/` → `clause_detail`

### `cases/templates/cases/case_detail.html`

#### HTML panel structure
- Removed Browse tab and Browse pane (replaced by in-line Browse All mode)
- Removed scope bar (replaced by scope pill in status line)
- Preview pane restructured: body scrolls independently; Insert/Cancel buttons pinned to bottom with `flex-shrink:0` so they are always visible regardless of clause length or panel height

#### JavaScript — new features
| Function | Purpose |
|---|---|
| `refLoadFullDoc()` | Fetches all 1,438 clauses; renders grouped by category with sticky headers |
| `renderFullDoc()` | Groups results by category → subcategory; renders category headers with "Search here" button |
| `refToggleBrowse()` | Toggles between Browse All and Recent view; updates button label |
| `refScopeToCategory(cat)` | Activates scoped search for a category; loads all section clauses immediately; shows scope pill |
| `refClearScope()` | Clears scope; re-runs query globally or returns to default view |
| `addRecentSearch(q)` | Saves search query to `localStorage['refLib_searches']` (capped at 10) |
| `getRecentSearches()` | Reads recent searches from localStorage |
| `clearRecentSearches()` | Clears search history |
| `refRunSearch(q)` | Re-runs a saved search query from a chip click |
| `clearRecent()` | Clears recently inserted clause history |
| `window.refLoadFullDoc` fallback fetch | If `clause.body` missing from cache, fetches `/api/clause/<id>/` and retries preview |

#### JavaScript — bug fixes
- **Section headers not clickable:** `list-group-item` class removed from category/subcategory dividers; `pointer-events:none` added so sticky headers cannot intercept clause button clicks
- **`JSON.stringify` in `onclick` broke "Search here":** moved to `data-scope-category` attribute read via event delegation
- **Event delegation scope button:** `panel.addEventListener` now catches `[data-scope-category]` before `[data-clause-id]`
- **Stale localStorage entries (missing body):** `openClausePreview` detects missing body and fetches fresh from `/api/clause/<id>/`; `addToRecent` purges bodyless entries on save; `getRecent` no longer silently drops them
- **Notes window auto-open:** removed `localStorage('notesWindowMinimized') === 'false'` logic; panel always starts hidden
- **Clear button disappearing:** "Recently Inserted" section header always renders; Clear button only shown when list is non-empty; empty state shows placeholder text
- **Search scope not respected:** `doRefSearch` now appends `&category=` to URL when `refScopeCategory` is set
- **Clearing search box resets scope:** `refClearSearch` sets `refScopeCategory = null`
- **Typing < 2 chars resets scope:** search input handler clears scope and restores default content

#### Default panel content (on open / search cleared)
1. **Recent Searches** — pill chips for last 10 queries; own Clear button; clicking chip re-runs search
2. **Recently Inserted** — last 25 inserted clauses; own Clear button; empty-state placeholder
3. **Common Notes** — `is_featured` clauses from `/api/featured/`

---

## Items from Enhancement Options Doc — Status

| # | Item | Status | Notes |
|---|---|---|---|
| 1 | Rich Text Preservation | **Done** | HTML bodies, full run-by-run parser |
| 2 | Highlight "Update Me" Cues | **Done** | `<mark>` emitted for yellow highlights |
| 3 | Clickable Hyperlinks | **Done** | `<a href>` from `<w:hyperlink>` rels |
| 4 | Image Support | **Deferred** | Option C: excluded by design for this cycle |
| 5 | Browse by Section | **Done** | Browse All with sticky category headers |
| 6 | Search Within a Section | **Done** | "Search here" button → scoped search + scope pill |
| 7 | Common Notes (Pinned) | **Done** | `is_featured` field + admin + `/api/featured/` |
| 8 | Recently Used Clauses | **Done** | localStorage (recently inserted + recent searches) |

---

## Data Actions Required After Deployment

1. **Reimport the Word document** via the admin reimport page (`/references/reimport/`) to populate `<mark>` highlight tags and ensure 1,438 clauses are on the TEST/PROD database. The parser supports marks; the data just needs a fresh import.

2. **Mark Common Notes in Django admin** (`/admin/references/referenceclause/`) — filter by category, check `is_featured` on the 20–30 high-frequency clauses to populate the Common Notes panel section.

---

## Smoke Test Results (Local)

Run: `python _temp_scripts/smoke_test_reflib.py`

- 16/20 checks pass
- 4 failures are **data gaps** (no featured clauses marked, no `<mark>` tags yet) — both resolved by reimport + admin curation above
- All 9 endpoint tests pass (search, scoped search, browse all, category browse, single clause, 404, short-query guard, featured, clauses-by-category)
