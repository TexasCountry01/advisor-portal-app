# Tech Notes Formatting — Options Analysis

**Date:** May 3, 2026  
**Issue:** When a Tech copies/pastes formatted content from the internal Google Doc template into the Technical Notes editor, all inline formatting is lost (red text, highlighted placeholders, bold section cues, etc.).

---

## Root Cause

TinyMCE 6's paste plugin **strips inline styles by default** when content is pasted from Google Docs. Colors (`color`) and highlights (`background-color`) are treated as external "dirty" styles and removed on paste.

The field itself (`report_notes_to_member`, stored as `HTMLField`) has no server-side sanitization — it stores whatever HTML it receives. The problem is entirely at the paste step in the editor.

The fix is one TinyMCE config option:
```javascript
paste_retain_style_values: 'all'   // or specific: 'color,background-color'
```

This would be added to both TinyMCE init blocks:
- `cases/templates/cases/case_detail.html` (floating notes window)
- `cases/templates/cases/case_completion_review.html` (completion review page)

---

## The Double-Edged Sword

Preserving paste formatting solves the tech's editing problem, but introduces a risk:

1. Tech copies template from Google Docs (red text = "update this", yellow highlight = placeholder data)
2. Pastes into TinyMCE → formatting now preserved ✅
3. Tech fills in case-specific data
4. **If tech forgets to remove internal color cues before releasing**, the advisor sees "UPDATE THIS FIELD" in red

---

## Options

### Option A — Quick Fix: Preserve paste styles + Clear Formatting button
**Effort:** ~20 minutes | **Risk:** Low

- Add `paste_retain_style_values: 'all'` to both TinyMCE init configs
- Add the `removeformat` button to both toolbars (already built into TinyMCE, just not on the toolbar)
- Tech can use "Clear Formatting" to strip all colors/highlights in one click before releasing

**Pro:** Done same day, minimal risk, unblocks techs immediately.  
**Con:** Relies on the tech to remember to clear internal formatting cues before releasing.

---

### Option B — Option A + "Preview as Advisor" button
**Effort:** ~1–2 hours | **Risk:** Low

Same as Option A, plus add a **"Preview as Advisor"** button next to the notes editor. When clicked, a modal renders the notes exactly as the advisor will see them — giving the tech a final visual check before releasing.

No second field, no database change, no backend change.

**Pro:** Gives the tech a clear "does this look right to the advisor?" check without changing any process.  
**Con:** Still relies on the tech to notice and fix leftover formatting in the preview.

---

### Option C — Two-Mode Notes: Working Copy + Clean Release Copy
**Effort:** ~3–4 hours | **Risk:** Medium (migration required)

- Add a second DB field: `report_notes_clean`
- Tech works in the full formatted version (colors, highlights, internal cues intact)
- When ready to release, a **"Finalize Notes"** action auto-strips colors/backgrounds and populates the clean field
- Tech can also manually edit the clean version before releasing
- **Advisors always see the clean version** — internal formatting never leaks out

**Pro:** Cleanly solves the double-edged sword. Internal editing cues stay internal by design.  
**Con:** Requires a migration, a second save path in views, and two rendering paths in templates.

---

### Option D — Placeholder System *(longer-term, "big idea" from 5/2)*
**Effort:** Significant design + dev work | **Risk:** Higher complexity

Formal `{{MEMBER_NAME}}`, `{{DOB}}`, `{{RETIREMENT_DATE}}` style placeholders in the template that auto-fill from case data at release time. No manual updating of highlighted fields needed. Eliminates the color-cue problem at the source — the template never needs "update this" markers because the system fills them automatically.

**Status:** Needs design work before implementation. Not an interim fix.

---

## Recommendation

**Implement Option A immediately** — it is a 4-line config change in two template files and unblocks the techs the same day. Adding the Clear Formatting button to the toolbar costs nothing extra since it already exists in TinyMCE.

**Add Option B on top of A** in the same sitting if a visual advisor-preview check is desired. The two together give the tech both the ability to paste with formatting and a way to verify the output looks clean before releasing.

**Revisit Option C** if, after using A+B for a few weeks, techs are still releasing notes with leftover internal colors. It becomes worth the migration effort only if the problem proves persistent.

**Option D** remains the long-term solution for the broader "formatted data" initiative.

---

## Affected Files (Options A & B)

| File | Change |
|------|--------|
| `cases/templates/cases/case_detail.html` | Add `paste_retain_style_values`, add `removeformat` to toolbar, optionally add preview button |
| `cases/templates/cases/case_completion_review.html` | Same TinyMCE config additions |

No backend changes, no migrations, no model changes required for Options A or B.
