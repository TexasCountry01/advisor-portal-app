# Feature Request: Row Highlighting in Dashboard Tables

**User Feedback:** *"It would be nice if we could isolate the current line of text we're in while working in the portal - like when you work in Excel - you can see what line you are actually on."*

**Date:** March 17, 2026  
**Status:** Under review

---

## Current Behavior

All four dashboards (Technician, Admin, Manager, Member) use Bootstrap's `table-hover` class, which provides a **very subtle pale gray** background on row hover. On wide tables with many columns, it's easy to lose track of which row you're on.

---

## Options

### Option 1: Stronger Hover Highlight (CSS only)

- More visible background color on hover (e.g., light blue like Excel)
- Applies automatically when the mouse moves over a row
- Simplest to implement — single CSS rule across all dashboards
- **Limitation:** Highlight disappears when the mouse moves away

### Option 2: Highlight + Left Border Accent (CSS only)

- Colored left border + stronger background on hover
- Makes the active row unmistakable even in a dense table
- Still CSS-only, no JavaScript needed
- **Limitation:** Same as Option 1 — disappears on mouse-out

### Option 3: Click-to-Lock Row Highlight (CSS + JavaScript)

- Click a row to keep it highlighted even without hovering
- Click again (or click another row) to move the highlight
- Closest to Excel's "selected cell" behavior
- Persistent — stays highlighted while you scroll or look elsewhere
- Requires a small JavaScript addition

---

## Recommendation

**Option 1 or 2** solves the core problem with minimal effort. Option 3 adds a nice touch if the user frequently needs to reference a specific row while looking at other parts of the screen.

All options are quick to implement and apply across all dashboards with a single change.
