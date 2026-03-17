# Feature Request: "Undo" Option for Notes Section

**User Feedback:** *"When using the notes section - it would be nice to have an 'undo' option - if something is accidentally deleted, the whole thing must be re-typed."*

**Date:** March 17, 2026  
**Status:** Under review

---

## What the User Is Experiencing

The Report Notes to Member editor (the floating TinyMCE window on the case detail page) has **auto-save with a 1-second debounce**. If a user accidentally selects all and deletes content — or makes any accidental large deletion — the auto-save fires 1 second later and **permanently overwrites the saved content** with the empty/deleted version.

- Ctrl+Z works **only** if the editor is still open and the user acts immediately
- If they refresh, navigate away, or don't realize it in time — the content is gone
- There is no version history, snapshots, or rollback mechanism

---

## How Auto-Save Works Today

1. User types in the TinyMCE editor
2. A `keyup`/`change` event fires
3. Previous save timer is cleared (debounce)
4. New 1-second timer starts
5. After 1 second of inactivity → AJAX POST sends the full editor content to the server
6. Server overwrites the saved notes — no backup of the previous version is kept

---

## All Notes Fields in the System

| Notes Type | Input Type | Auto-Save? | Undo Risk |
|-----------|-----------|-----------|-----------|
| Report Notes to Member | TinyMCE (rich text) | Yes (1s debounce) | **HIGH** — auto-save locks in mistakes |
| Special Notes (member) | Plain textarea | No (manual save) | Low — append-only, old notes preserved |
| Document Notes | Plain textarea | No (manual save) | Low — tied to document upload |
| Resubmission Notes | Plain textarea | No (manual save) | Low — one-time entry |
| Case Submission Notes | Plain textarea | No (manual save) | Low — one-time entry |
| Internal Case Notes | Plain textarea | No (AJAX submit) | Low — add new / delete old pattern |
| Review Notes (staff) | Plain textarea | No (manual save) | Low |
| Rejection Notes (staff) | Plain textarea | No (manual save) | Low |

**The problem is isolated to Report Notes to Member** — the only field with auto-save that overwrites in place.

---

## Proposed Solutions

### Option 1: Confirm Before Saving Empty Content (Simplest)

- If auto-save detects the editor is now empty (or near-empty) but previously had substantial content, **pause auto-save and prompt** "Your notes appear to be empty — save anyway?"
- Prevents the most common accident (select-all + delete)
- No database changes needed
- **Limitation:** Doesn't help with partial accidental deletions

### Option 2: Keep Last N Snapshots (Moderate)

- Add a `ReportNotesHistory` model that stores the previous version(s) before each auto-save
- Include a "Restore Previous Version" button in the floating notes window
- Staff can see a short list of recent snapshots with timestamps and restore any one
- **Limitation:** Small database growth over time (can be pruned)

### Option 3: Full Version History (Most Complete)

- A `ReportNotesHistory` table logs every auto-save with timestamp and user
- Browsable version history with diff view
- One-click restore to any previous version
- **Limitation:** Most complex to build; may be more than needed

---

## Recommendation

**Option 2 (Keep Last N Snapshots)** provides the best balance:

- Solves the user's core problem — accidental deletions can be recovered
- Covers both full and partial deletions
- Simple UI: a "Restore" button with a dropdown of recent versions
- Can limit to last 10 snapshots per case to control database size
- Could be combined with Option 1's empty-content warning for extra safety
